from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any

from news_helper.config import get_float_env, get_int_env
from news_helper.llm.openai_client import DEFAULT_OPENAI_MODEL, generate_json
from news_helper.text_match import find_term


DEFAULT_THRESHOLD = 0.4
DEFAULT_MAX_ARTICLE_CHARS = 6000

INCLUDE_TERM_TYPES = {
    "economic_concept",
    "financial_instrument",
    "policy_or_regulation",
    "indicator",
    "accounting_term",
    "legal_administrative_term",
    "labor_relations_term",
    "business_management_term",
    "industry_technology_term",
    "real_estate_term",
    "insurance_actuarial_term",
    "debt_restructuring_term",
}

ALL_TERM_TYPES = [
    "economic_concept",
    "financial_instrument",
    "policy_or_regulation",
    "indicator",
    "accounting_term",
    "legal_administrative_term",
    "labor_relations_term",
    "business_management_term",
    "industry_technology_term",
    "real_estate_term",
    "insurance_actuarial_term",
    "debt_restructuring_term",
    "company_name",
    "person_name",
    "place_name",
    "general_word",
    "sentence_fragment",
]

current_file_path = Path(__file__).resolve()
project_root = current_file_path.parent.parent.parent
DEFAULT_DICT_PATH = str(project_root / "data" / "terms_800_preprocessed.json")


@dataclass(frozen=True)
class DifficultTerm:
    term: str
    difficulty_score: float
    explanation: str
    canonical_term: str | None = None
    variants: tuple[str, ...] = ()
    source: str = "llm"
    term_type: str = "economic_concept"
    highlight_decision: str = "include"
    exclude_reason: str | None = None
    is_minimal_term: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "term": self.term,
            "canonical_term": self.canonical_term or self.term,
            "variants": list(self.variants),
            "difficulty_score": self.difficulty_score,
            "explanation": self.explanation,
            "source": self.source,
            "term_type": self.term_type,
            "highlight_decision": self.highlight_decision,
            "exclude_reason": self.exclude_reason,
            "is_minimal_term": self.is_minimal_term,
        }


@dataclass(frozen=True)
class TermAnalysisResult:
    title: str | None
    threshold: float
    model: str
    difficult_terms: list[DifficultTerm]
    analysis_mode: str = "hybrid"
    llm_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "threshold": self.threshold,
            "model": self.model,
            "analysis_mode": self.analysis_mode,
            "llm_error": self.llm_error,
            "difficult_terms": [term.to_dict() for term in self.difficult_terms],
        }


def analyze_difficult_terms(
    article_body: str,
    title: str | None = None,
    threshold: float | None = None,
) -> TermAnalysisResult:
    resolved_threshold = threshold if threshold is not None else get_float_env("DIFFICULTY_THRESHOLD", DEFAULT_THRESHOLD)
    model = os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    
    # 1. 룰베이스 사전 매칭 실행
    dict_path = os.getenv("ECONOMIC_DICT_PATH", DEFAULT_DICT_PATH)
    rule_based_terms = _apply_rule_based_matching(article_body, dict_path)
    
    # 2. LLM 프롬프트 생성 (룰베이스로 찾은 단어 리스트를 함께 전달)
    prompt = _build_prompt(
        article_body=article_body, 
        title=title, 
        threshold=resolved_threshold,
        rule_based_terms=rule_based_terms 
    )
    
    # 3. LLM API 호출 및 결과 생성
    payload = generate_json(
        prompt=prompt,
        response_schema=_response_schema(),
        model=model,
    )

    # 4. LLM 결과와 룰베이스 결과를 통합합니다.
    # LLM이 사전 매칭 단어를 누락하더라도 룰베이스 결과는 최종 결과에 남깁니다.
    llm_terms = _normalize_terms(payload.get("difficult_terms", []), resolved_threshold, article_body)
    final_terms = _merge_rule_and_llm_terms(rule_based_terms, llm_terms, article_body)

    return TermAnalysisResult(
        title=title,
        threshold=resolved_threshold,
        model=model,
        difficult_terms=final_terms,
        analysis_mode="hybrid" if rule_based_terms else "llm_only",
    )


def _apply_rule_based_matching(article_body: str, dict_path: str) -> list[DifficultTerm]:
    """경제 사전 JSON을 바탕으로 본문에서 단어를 1차 매칭합니다."""
    if not Path(dict_path).exists():
        print(f"⚠️ 룰베이스 사전을 찾을 수 없습니다: {dict_path}")
        return []
        
    try:
        with open(dict_path, 'r', encoding='utf-8') as f:
            economic_dict = json.load(f)
    except Exception as e:
        print(f"⚠️ 사전 로드 실패: {e}")
        return []

    matched_terms = []
    seen_keys = set()
    
    search_pool = []
    for item in economic_dict:
        canonical_term = _clean_term(str(item.get("term", "")))
        definition = item.get('definition', '')
        variants = tuple(_dedupe_terms([canonical_term, *item.get('variants', [])]))
        for search_word in variants:
            search_pool.append((search_word, canonical_term, variants, definition))
            
    # 긴 단어(예: 부실채권(NPL))부터 매칭되도록 길이 역순 정렬
    search_pool.sort(key=lambda x: len(x[0]), reverse=True)
    
    for search_word, canonical_term, variants, definition in search_pool:
        canonical_key = _canonical_key(canonical_term or search_word)
        if find_term(article_body, search_word) != -1 and canonical_key not in seen_keys:
            matched_terms.append(DifficultTerm(
                term=search_word,
                difficulty_score=1.0, 
                explanation=definition,
                canonical_term=canonical_term or search_word,
                variants=variants,
                source="rule",
                term_type="economic_concept",
                highlight_decision="include",
                is_minimal_term=True,
            ))
            seen_keys.add(canonical_key)
            
    return matched_terms


def _build_prompt(article_body: str, title: str | None, threshold: float, rule_based_terms: list[DifficultTerm]) -> str:
    """LLM 분석을 위한 프롬프트를 구성합니다."""
    max_chars = get_int_env("LLM_MAX_ARTICLE_CHARS", DEFAULT_MAX_ARTICLE_CHARS)
    clipped_body = article_body[:max(1000, max_chars)]
    title_line = title or "제목 없음"
    
    rule_based_instruction = ""
    if rule_based_terms:
        dict_text = "\n".join(
            [
                f"- 본문 표기: {t.term}\n  대표 용어: {t.canonical_term or t.term}\n"
                f"  동의 표기: {', '.join(t.variants)}\n  원본 설명: {t.explanation}"
                for t in rule_based_terms
            ]
        )
        rule_based_instruction = f"""
[사전 매칭 단어 및 원본 설명]
{dict_text}

[사전 매칭 단어 처리 규칙]
위 [사전 매칭 단어]들은 본문에 등장한 단어이므로 무조건 결과(difficult_terms)에 포함시킨다. 단, 다음 규칙을 엄격히 따른다:
1. 원본 설명에 포함된 의미 없는 자음/모음(예: 'ㅊ' 등), 잘못된 띄어쓰기, 줄바꿈 오류를 문맥에 맞게 자연스럽게 교정한다.
2. 원본 설명의 핵심 내용을 활용하여 1~2문장으로 짧게 요약하여 작성한다. (절대 원본에 없는 내용을 임의로 지어내지 말 것).
3. 문체는 반드시 친절한 '-습니다/-ㅂ니다' 체로 변환한다.
4. 의미와 설명이 동일한 단어가 중복 매칭되어 있다면, 본문 문맥에 가장 적합한 대표 표현 1개로 통합한다.
"""

    return f"""
너는 경제 입문 일반인을 돕는 한국어 경제 뉴스 학습 도우미다.
{rule_based_instruction}
작업:
1. [사전 매칭 단어]가 있다면 위 처리 규칙에 따라 교정하여 결과에 포함한다.
2. 추가로 아래 뉴스 본문을 스캔하여, 사전 매칭 단어 외에 일반인이 이해하기 어려울 경제 용어를 찾는다.
3. 새롭게 찾은 단어도 난이도 점수가 {threshold} 이상인 것만 포함하며, 설명은 1~2문장의 '-습니다/-ㅂ니다' 체로 짧게 작성한다.

공통 규칙:
- term은 본문에 실제로 등장한 표기 그대로 작성한다.
- canonical_term은 같은 개념을 묶기 위한 대표 용어로 작성한다. 괄호 속 약어만 다르거나 영문 대소문자만 다른 표현은 같은 canonical_term을 사용한다.
- variants에는 본문 표기, 약어, 괄호 포함 표기 등 같은 개념을 가리키는 표현을 모두 넣는다.
- 같은 의미의 단어가 여러 번 나오면 한 번만 포함한다.
- term_type은 반드시 다음 중 하나로 분류한다: {", ".join(ALL_TERM_TYPES)}.
- highlight_decision은 include 또는 exclude 중 하나로 작성한다.
- exclude_reason은 include일 때 빈 문자열, exclude일 때 제외 사유를 간단히 작성한다.
- is_minimal_term은 term이 문장 일부가 아니라 독립적인 최소 용어이면 true로 작성한다.
- 긴 표현이어도 하나의 제도명, 계약명, 지표명, 절차명, 상품명, 산업/기술 용어, 노동/법률/부동산 실무 용어로 쓰이면 is_minimal_term=true로 둔다.
- 단순 수식어가 붙은 설명 구절이거나 문장 일부를 잘라낸 표현이면 is_minimal_term=false로 둔다.
- 너무 일반적인 단어, 인명, 지명, 단순 회사명, 문장 일부를 길게 잘라낸 표현은 highlight_decision을 exclude로 둔다.
- 노동·노사, 법·행정 절차, 산업기술, 경영관리, 부동산 거래, 보험/계리, 채무조정 관련 실무 용어는 일반 독자가 이해하기 어려우면 include 대상으로 본다.
- difficulty_score는 0.0 이상 1.0 이하 숫자로 작성한다. (사전 단어는 1.0 권장)
- JSON만 반환한다.

뉴스 제목:
{title_line}

뉴스 본문:
{clipped_body}
""".strip()


def _response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "difficult_terms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "term": {
                            "type": "string",
                            "description": "뉴스 본문에 실제로 등장한 어려운 단어",
                        },
                        "canonical_term": {
                            "type": "string",
                            "description": "약어와 괄호 표기를 제거하거나 대표 표현으로 통일한 용어",
                        },
                        "variants": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "같은 개념을 가리키는 본문 표기, 약어, 괄호 표기",
                        },
                        "term_type": {
                            "type": "string",
                            "enum": ALL_TERM_TYPES,
                        },
                        "highlight_decision": {
                            "type": "string",
                            "enum": ["include", "exclude"],
                        },
                        "exclude_reason": {
                            "type": "string",
                            "description": "include이면 빈 문자열, exclude이면 제외 사유",
                        },
                        "is_minimal_term": {
                            "type": "boolean",
                            "description": "독립적인 최소 용어인지 여부",
                        },
                        "difficulty_score": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "explanation": {
                            "type": "string",
                            "description": "경제 입문자를 위한 쉬운 한국어 설명",
                        },
                    },
                    "required": [
                        "term",
                        "canonical_term",
                        "variants",
                        "term_type",
                        "highlight_decision",
                        "exclude_reason",
                        "is_minimal_term",
                        "difficulty_score",
                        "explanation",
                    ],
                },
            }
        },
        "required": ["difficult_terms"],
    }


def _normalize_terms(raw_terms: Any, threshold: float, article_body: str) -> list[DifficultTerm]:
    if not isinstance(raw_terms, list):
        return []

    normalized: list[DifficultTerm] = []
    seen: set[str] = set()

    for raw in raw_terms:
        if not isinstance(raw, dict):
            continue

        raw_variants = raw.get("variants", [])
        variants = raw_variants if isinstance(raw_variants, list) else []
        canonical_term = _clean_term(str(raw.get("canonical_term") or raw.get("term", "")))
        term = _resolve_surface_term(
            article_body,
            [str(raw.get("term", "")), canonical_term, *[str(item) for item in variants]],
        )
        if not term:
            continue

        try:
            score = float(raw.get("difficulty_score", 0.0))
        except (TypeError, ValueError):
            continue

        score = max(0.0, min(1.0, score))
        if score < threshold:
            continue

        explanation = _clean_explanation(str(raw.get("explanation", "")))
        if not explanation:
            continue

        aliases = tuple(_dedupe_terms([term, canonical_term, *variants]))
        canonical_key = _canonical_key(canonical_term or term)
        if canonical_key in seen:
            continue
        term_type = _clean_term(str(raw.get("term_type", "")))
        highlight_decision = _clean_term(str(raw.get("highlight_decision", "")))
        exclude_reason = _clean_explanation(str(raw.get("exclude_reason", ""))) or None
        is_minimal_term = bool(raw.get("is_minimal_term", False))
        if not _should_include_structured_term(term_type, highlight_decision, is_minimal_term):
            continue

        normalized.append(
            DifficultTerm(
                term=term,
                difficulty_score=score,
                explanation=explanation,
                canonical_term=canonical_term or term,
                variants=aliases,
                source="llm",
                term_type=term_type,
                highlight_decision=highlight_decision,
                exclude_reason=exclude_reason,
                is_minimal_term=is_minimal_term,
            )
        )
        seen.add(canonical_key)

    normalized.sort(key=lambda item: (-item.difficulty_score, item.term))
    return normalized


def _merge_rule_and_llm_terms(
    rule_based_terms: list[DifficultTerm],
    llm_terms: list[DifficultTerm],
    article_body: str,
) -> list[DifficultTerm]:
    merged: dict[str, DifficultTerm] = {}

    for term in llm_terms:
        cleaned_term = _clean_term(term.term)
        if not cleaned_term or find_term(article_body, cleaned_term) == -1:
            continue
        canonical_term = _clean_term(term.canonical_term or cleaned_term)
        merged[_canonical_key(canonical_term)] = DifficultTerm(
            term=cleaned_term,
            difficulty_score=max(0.0, min(1.0, term.difficulty_score)),
            explanation=_clean_explanation(term.explanation),
            canonical_term=canonical_term,
            variants=tuple(_dedupe_terms([cleaned_term, canonical_term, *term.variants])),
            source=term.source or "llm",
            term_type=term.term_type,
            highlight_decision=term.highlight_decision,
            exclude_reason=term.exclude_reason,
            is_minimal_term=term.is_minimal_term,
        )

    for term in rule_based_terms:
        cleaned_term = _clean_term(term.term)
        if not cleaned_term or find_term(article_body, cleaned_term) == -1:
            continue

        canonical_term = _clean_term(term.canonical_term or cleaned_term)
        canonical_key = _canonical_key(canonical_term)
        existing = merged.get(canonical_key)
        if existing is not None:
            merged[canonical_key] = DifficultTerm(
                term=existing.term,
                difficulty_score=max(existing.difficulty_score, term.difficulty_score),
                explanation=existing.explanation,
                canonical_term=existing.canonical_term or canonical_term,
                variants=tuple(_dedupe_terms([*existing.variants, cleaned_term, canonical_term, *term.variants])),
                source="hybrid",
                term_type=existing.term_type,
                highlight_decision=existing.highlight_decision,
                exclude_reason=existing.exclude_reason,
                is_minimal_term=existing.is_minimal_term,
            )
            continue

        explanation = _clean_explanation(term.explanation)
        if explanation:
            merged[canonical_key] = DifficultTerm(
                term=cleaned_term,
                difficulty_score=max(0.0, min(1.0, term.difficulty_score)),
                explanation=explanation,
                canonical_term=canonical_term,
                variants=tuple(_dedupe_terms([cleaned_term, canonical_term, *term.variants])),
                source=term.source or "rule",
                term_type=term.term_type,
                highlight_decision=term.highlight_decision,
                exclude_reason=term.exclude_reason,
                is_minimal_term=term.is_minimal_term,
            )

    return _finalize_terms(list(merged.values()))


def _finalize_terms(terms: list[DifficultTerm]) -> list[DifficultTerm]:
    return sorted(terms, key=lambda item: (-item.difficulty_score, item.term))


def _clean_term(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _clean_explanation(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _should_include_structured_term(
    term_type: str,
    highlight_decision: str,
    is_minimal_term: bool,
) -> bool:
    return (
        highlight_decision == "include"
        and is_minimal_term
        and term_type in INCLUDE_TERM_TYPES
    )


def _dedupe_terms(values: list[str] | tuple[str, ...]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_term(str(value))
        if not cleaned:
            continue
        key = _surface_key(cleaned)
        if key in seen:
            continue
        deduped.append(cleaned)
        seen.add(key)
    return deduped


def _resolve_surface_term(article_body: str, candidates: list[str]) -> str:
    for candidate in sorted(_dedupe_terms(candidates), key=len, reverse=True):
        if find_term(article_body, candidate) != -1:
            return candidate
    return ""


def _canonical_key(value: str) -> str:
    cleaned = _clean_term(value).lower()
    cleaned = re.sub(r"\([^)]*\)", "", cleaned)
    cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
    cleaned = re.sub(r"[`'\"·ㆍ\-/_,.:;|()\[\]{}]", "", cleaned)
    return re.sub(r"\s+", "", cleaned)


def _surface_key(value: str) -> str:
    return re.sub(r"\s+", "", _clean_term(value).lower())
