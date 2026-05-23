"""
불/베어 에이전트 공통 LLM 호출 레이어

두 에이전트의 API 호출·JSON 파싱·오류 처리 로직을 공유합니다.
"""

import json
import os
import re

from openai import OpenAI
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

_GLOSSARY_PATH = os.path.join(os.path.dirname(__file__), "field_glossary.json")


def _load_glossary_section() -> str:
    """field_glossary.json을 읽어 시스템 프롬프트용 compact 텍스트로 변환."""
    try:
        with open(_GLOSSARY_PATH, encoding="utf-8") as f:
            g = json.load(f)
        lines = []
        for group, fields in g.items():
            if group.startswith("_"):
                continue
            for key, desc in fields.items():
                lines.append(f"  {group}.{key}: {desc}")
        return "\n[데이터 필드 해석 가이드]\n아래 필드명의 의미를 참고해 claim을 자연어로 작성하세요.\n" + "\n".join(lines) + "\n"
    except Exception:
        return ""


# ── 필드명 → 자연어 레이블 치환 테이블 ───────────────────────────
_FIELD_LABELS: dict[str, str] = {
    # technical
    "disparity_20":         "20일 이격도",
    "volume_spike":         "거래량 급등",
    "volume_change_5d":     "5일 거래량 변화율",
    "rsi_14":               "RSI",
    "macd_signal":          "MACD 신호",
    "bollinger_position":   "볼린저 밴드 위치",
    "golden_cross_20_60":   "골든크로스(MA20↑MA60)",
    "dead_cross_20_60":     "데드크로스(MA20↓MA60)",
    "support_level":        "지지선",
    "resistance_level":     "저항선",
    # macd/bollinger 값 레이블
    "bullish_crossover":    "MACD 상향 돌파",
    "bearish_crossover":    "MACD 하향 돌파",
    "upper_band_near":      "볼린저 밴드 상단 근접",
    "lower_band_near":      "볼린저 밴드 하단 근접",
    # macro
    "fsi_factor_score":     "금융스트레스지수(FSI)",
    "regime_probabilities": "시장 국면 확률",
    "state_0_normal":       "정상 국면",
    "state_1_caution":      "주의 국면",
    "state_2_crisis":       "위기 국면",
    "markov_converged":     "마코프 모형 수렴",
    "dod_change_pct":       "전일 대비 등락률",
    "wow_change_pt":        "전주 대비 변화폭",
    "Term_Spread":          "장단기 금리차",
    "Credit_Spread":        "신용 스프레드",
    "CP_Spread":            "CP 스프레드",
    "Bank_Bond_Spread":     "은행채 스프레드",
    # sector - valuation
    "per_band":             "PER 밴드",
    "pbr_band":             "PBR 밴드",
    "per_label":            "PER 평가",
    "pbr_label":            "PBR 평가",
    "eps_trend":            "EPS 추세",
    "eps_yoy_chg":          "EPS YoY 변화율",
    "pct_3y":               "3년 히스토리 백분위",
    # sector - supply demand
    "foreign_consecutive_sell": "외국인 연속 매도 일수",
    "foreign_consecutive_buy":  "외국인 연속 매수 일수",
    "institutional_5d_net":     "기관 5일 누적 순매수",
    "institutional_5d_trend":   "기관 5일 수급 방향",
    "trend_consistency":        "단기·중기 수급 방향 일치",
    "intensity_change":         "수급 강도 변화",
    # sector - relative strength
    "rs_history":           "기간별 상대강도",
    "rs_trend":             "상대강도 추세",
    "sector_issue":         "섹터·종목 진단",
    "strongest_period":     "최강 상대강도 구간",
    # sentiment
    "sentiment_label":      "시장 심리",
    "sentiment_score":      "심리 점수",
    "vkospi":               "VKOSPI(공포지수)",
    "foreign_flow":         "외국인 수급",
    "market_momentum":      "시장 모멘텀",
    "panic":                "패닉 신호",
    "fomo":                 "FOMO(과열) 신호",
    "risk_signal":          "위험 신호",
    "net_buy":              "순매수",
    "trend":                "방향",
    "change_weekly":        "주간 변화",
    "kospi_change":         "KOSPI 등락률",
    "wow_change":           "전주 대비 변화",
    "dod_change":           "전일 대비 변화",
}


def _sanitize_text(text: str) -> str:
    """LLM 출력 텍스트에서 필드명을 자연어 레이블로 강제 치환.

    Python \b 는 한국어 조사(이/는/가 등)를 단어 문자로 취급해
    'sentiment_label이' 같은 패턴을 잡지 못하므로
    ASCII 전용 경계 (?<![a-zA-Z0-9_]) / (?![a-zA-Z0-9_]) 를 사용한다.
    """
    if not isinstance(text, str):
        return text
    # 점(.) 표기 경로를 먼저 처리 (예: risk_signal.panic, sentiment.foreign_flow.net_buy)
    _DOT_PATHS = [
        (r"risk_signal\.panic",                "패닉 신호"),
        (r"risk_signal\.fomo",                 "FOMO(과열) 신호"),
        (r"sentiment\.foreign_flow\.net_buy",  "외국인 순매수"),
        (r"sentiment\.foreign_flow\.trend",    "외국인 수급 방향"),
        (r"sentiment\.analysis\.sentiment_label",  "시장 심리"),
        (r"sentiment\.analysis\.sentiment_score",  "심리 점수"),
        (r"macro\.quantitative_models\.regime_probabilities", "시장 국면 확률"),
    ]
    for path_pat, path_label in _DOT_PATHS:
        text = re.sub(path_pat, path_label, text)

    # 단일 필드명 치환 (ASCII 경계 사용 — 한국어 조사 앞에서도 동작)
    lb = r"(?<![a-zA-Z0-9_])"
    rb = r"(?![a-zA-Z0-9_])"
    for field, label in sorted(_FIELD_LABELS.items(), key=lambda x: -len(x[0])):
        p = re.escape(field)
        text = re.sub(rf"{lb}{p}=true{rb}",  f"{label}(감지됨)", text, flags=re.IGNORECASE)
        text = re.sub(rf"{lb}{p}=false{rb}", f"{label}(없음)",   text, flags=re.IGNORECASE)
        text = re.sub(rf"{lb}{p}{rb}",       label,              text)

    # 필드 치환 후 남은 standalone true/false 정리
    text = re.sub(rf"{lb}true{rb}",  "감지됨", text, flags=re.IGNORECASE)
    text = re.sub(rf"{lb}false{rb}", "미감지", text, flags=re.IGNORECASE)
    return text


def _sanitize_output(result: dict) -> dict:
    """파싱된 LLM JSON의 텍스트 필드 전체에 필드명 치환을 적용."""
    if not isinstance(result, dict):
        return result
    for arg in result.get("arguments") or []:
        if isinstance(arg, dict):
            arg["claim"] = _sanitize_text(arg.get("claim", ""))
    result["rebuttal"] = _sanitize_text(result.get("rebuttal") or "") or None
    result["summary"]  = _sanitize_text(result.get("summary", ""))
    return result


def _json_default(obj):
    """numpy scalar 등 비직렬화 타입을 Python 기본 타입으로 변환"""
    if hasattr(obj, "item"):
        return obj.item()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _call_llm(
    system_prompt: str,
    input_package: dict,
    opponent_argument: dict | None,
    opponent_label: str,
    model: str,
) -> dict:
    """
    OpenAI API를 호출하고 JSON 응답을 파싱합니다.

    Args:
        system_prompt:      에이전트별 시스템 프롬프트 (불/베어 구분)
        input_package:      불/베어 공통 입력 패키지 (spec §5)
        opponent_argument:  직전 라운드 상대방 출력 dict (없으면 None)
        opponent_label:     상대방 역할명 (예: "Bear", "Bull")
        model:              OpenAI 모델 ID

    Returns:
        dict: 에이전트 출력 JSON
              오류 시 {"error": str, "raw_response": str (있을 경우)}
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요."}

    full_system_prompt = system_prompt + _load_glossary_section()

    opponent_section = (
        json.dumps(opponent_argument, ensure_ascii=False, indent=2)
        if opponent_argument
        else "없음 (첫 번째 라운드)"
    )

    user_message = (
        f"[분석 대상]\n{input_package.get('topic', '종목 분석')}\n\n"
        f"[입력 데이터 패키지]\n"
        f"{json.dumps(input_package, ensure_ascii=False, indent=2, default=_json_default)}\n\n"
        f"[상대방({opponent_label}) 논거]\n{opponent_section}\n\n"
        f"위 데이터를 분석하여 지정된 JSON 형식으로 출력하세요."
    )

    raw = ""
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            max_completion_tokens=1024,
            messages=[
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        raw = response.choices[0].message.content.strip()

        # 모델이 마크다운 코드블록으로 감쌀 경우 제거
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return _sanitize_output(json.loads(raw))

    except json.JSONDecodeError as e:
        return {"error": f"JSON 파싱 실패: {e}", "raw_response": raw}
    except Exception as e:
        return {"error": str(e)}
