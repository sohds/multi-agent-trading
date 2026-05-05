"""
백테스팅용 마스킹 함수 모듈

목적: LLM 데이터 누수 차단
- 종목명/티커/날짜를 익명화 (gpt-5.4-mini가 학습 데이터에서 본 시점·종목 인식 방지)
- 절대 가격을 ma_200 기준 비율로 정규화 (RSI, MACD 등 상대 지표는 그대로 유지)

상대 지표(disparity_20, RSI, MACD, 골든크로스 등)는 이미 정규화돼 있어 식별 단서가 약하다.
"""

from typing import Any


_PRICE_FIELDS = (
    "price",
    "ma_5", "ma_20", "ma_60", "ma_120", "ma_200",
    "support_level", "resistance_level",
)


def mask_technical(tech: dict[str, Any]) -> dict[str, Any]:
    """
    technical 지표 dict를 마스킹.

    - ticker → "STOCK_A"
    - name   → "종목 A"
    - date   → "T+0"
    - price/MA/지지·저항: ma_200 기준 비율로 정규화 (소수 4자리)

    ma_200이 None이면 ma_60 → ma_20 → price 순으로 fallback.
    모두 None이면 절대값 유지(드문 케이스).

    Args:
        tech: get_technical_indicators() 출력 dict

    Returns:
        마스킹된 dict (원본은 변경하지 않음)
    """
    if not isinstance(tech, dict) or "error" in tech:
        return tech

    out = dict(tech)
    out["ticker"] = "STOCK_A"
    out["name"]   = "종목 A"
    out["date"]   = "T+0"

    base = (
        out.get("ma_200")
        or out.get("ma_60")
        or out.get("ma_20")
        or out.get("price")
    )
    if not base:
        return out

    for field in _PRICE_FIELDS:
        val = out.get(field)
        if val is not None:
            out[field] = round(val / base, 4)

    return out
