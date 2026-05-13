from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
from typing import Any

from news_helper.config import get_float_env, get_int_env
from news_helper.llm.openai_client import DEFAULT_OPENAI_MODEL, generate_json


DEFAULT_THRESHOLD = 0.5
DEFAULT_MAX_ARTICLE_CHARS = 6000

current_file_path = Path(__file__).resolve()
project_root = current_file_path.parent.parent.parent
DEFAULT_DICT_PATH = str(project_root / "data" / "terms_800_preprocessed.json")


@dataclass(frozen=True)
class DifficultTerm:
    term: str
    difficulty_score: float
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TermAnalysisResult:
    title: str | None
    threshold: float
    model: str
    difficult_terms: list[DifficultTerm]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "threshold": self.threshold,
            "model": self.model,
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

    # 4. LLM 결과 정규화 (LLM이 교정한 사전 단어 + 새로 분석한 단어 통합)
    final_terms = _normalize_terms(payload.get("difficult_terms", []), resolved_threshold, article_body)

    return TermAnalysisResult(
        title=title,
        threshold=resolved_threshold,
        model=model,
        difficult_terms=final_terms,
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
    seen_definitions = set() # 뜻(definition)을 기준으로 중복 매칭 방지
    
    search_pool = []
    for item in economic_dict:
        orig_term = item['term']
        definition = item.get('definition', '')
        search_pool.append((orig_term, definition))
        for variant in item.get('variants', []):
            search_pool.append((variant, definition))
            
    # 긴 단어(예: 부실채권(NPL))부터 매칭되도록 길이 역순 정렬
    search_pool.sort(key=lambda x: len(x[0]), reverse=True)
    
    for search_word, definition in search_pool:
        # 본문에 단어가 있고, 동일한 뜻의 단어가 아직 추가되지 않았을 때만 포함
        if search_word in article_body and definition not in seen_definitions:
            matched_terms.append(DifficultTerm(
                term=search_word,
                difficulty_score=1.0, 
                explanation=definition
            ))
            seen_definitions.add(definition)
            
    return matched_terms


def _build_prompt(article_body: str, title: str | None, threshold: float, rule_based_terms: list[DifficultTerm]) -> str:
    """LLM 분석을 위한 프롬프트를 구성합니다."""
    max_chars = get_int_env("LLM_MAX_ARTICLE_CHARS", DEFAULT_MAX_ARTICLE_CHARS)
    clipped_body = article_body[:max(1000, max_chars)]
    title_line = title or "제목 없음"
    
    rule_based_instruction = ""
    if rule_based_terms:
        dict_text = "\n".join([f"- 단어: {t.term}\n  원본 설명: {t.explanation}" for t in rule_based_terms])
        rule_based_instruction = f"""
[사전 매칭 단어 및 원본 설명]
{dict_text}

[사전 매칭 단어 처리 규칙]
위 [사전 매칭 단어]들은 본문에 등장한 단어이므로 무조건 결과(difficult_terms)에 포함시킨다. 단, 다음 규칙을 엄격히 따른다:
1. 원본 설명에 포함된 의미 없는 자음/모음(예: 'ㅊ' 등), 잘못된 띄어쓰기, 줄바꿈 오류를 문맥에 맞게 자연스럽게 교정한다.
2. 원본 설명의 핵심 내용을 활용하여 3~4문장 내외로 요약하여 작성한다. (절대 원본에 없는 내용을 임의로 지어내지 말 것).
3. 문체는 반드시 친절한 '-습니다/-ㅂ니다' 체로 변환한다.
4. 의미와 설명이 동일한 단어가 중복 매칭되어 있다면, 본문 문맥에 가장 적합한 대표 표현 1개로 통합한다.
"""

    return f"""
너는 경제 입문 일반인을 돕는 한국어 경제 뉴스 학습 도우미다.
{rule_based_instruction}
작업:
1. [사전 매칭 단어]가 있다면 위 처리 규칙에 따라 교정하여 결과에 포함한다.
2. 추가로 아래 뉴스 본문을 스캔하여, 사전 매칭 단어 외에 일반인이 이해하기 어려울 경제 용어를 찾는다.
3. 새롭게 찾은 단어도 난이도 점수가 {threshold} 이상인 것만 포함하며, 설명은 3~4문장의 '-습니다/-ㅂ니다' 체로 작성한다.

공통 규칙:
- term은 본문에 실제로 등장한 표기 그대로 작성한다.
- 같은 의미의 단어가 여러 번 나오면 한 번만 포함한다.
- 너무 일반적인 단어, 인명, 지명, 단순 회사명은 제외한다.
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
                    "required": ["term", "difficulty_score", "explanation"],
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

        term = _clean_term(str(raw.get("term", "")))
        if not term or term in seen:
            continue
        if term not in article_body:
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

        normalized.append(DifficultTerm(term=term, difficulty_score=score, explanation=explanation))
        seen.add(term)

    normalized.sort(key=lambda item: (-item.difficulty_score, item.term))
    return normalized


def _clean_term(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _clean_explanation(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()