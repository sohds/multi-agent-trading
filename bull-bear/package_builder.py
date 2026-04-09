"""
불/베어 공통 입력 패키지 조립 모듈

각 에이전트(technical, macro, sector, sentiment)의 출력을 받아
spec §5 형식의 단일 입력 패키지로 조립합니다.

사용법:
    from package_builder import build_input_package

    pkg = build_input_package(
        ticker="005930",
        ticker_name="삼성전자",
        sector_payload=run_sector_agent(...),   # 또는 None
        macro_payload=run_macro_agent(),         # 또는 None
        sentiment_payload=None,                  # 팀원 미구현
    )
"""

import sys
import os

# bull-bear/ 를 sys.path에 추가 (collectors 임포트용)
sys.path.insert(0, os.path.dirname(__file__))

from collectors.technical_indicators import get_technical_indicators


def build_input_package(
    ticker: str,
    ticker_name: str,
    sector_payload: dict | None = None,
    macro_payload: dict | None = None,
    sentiment_payload: dict | None = None,
    topic_type: str = "종목",
) -> dict:
    """
    불/베어 공통 입력 패키지 생성 (spec §5)

    Args:
        ticker:           종목 코드 (예: "005930")
        ticker_name:      종목명 (예: "삼성전자")
        sector_payload:   run_sector_agent() 반환값. None이면 sector 필드 null
        macro_payload:    run_macro_agent() 반환값. None이면 macro 필드 null
        sentiment_payload: sentiment 에이전트 반환값. None이면 null (현재 미구현)
        topic_type:       "종목" | "시장전체" | "테마"

    Returns:
        dict: 불/베어 에이전트에 전달할 공통 입력 패키지
    """

    # ── 1. technical ───────────────────────────────────────────
    technical = get_technical_indicators(ticker, ticker_name)

    # ── 2. macro: meta, errors 제외 (spec §4-1) ─────────────────
    macro = None
    if macro_payload:
        macro = {
            "raw_indicators":    macro_payload.get("raw_indicators"),
            "quantitative_models": macro_payload.get("quantitative_models"),
            "objective_analysis":  macro_payload.get("objective_analysis"),
        }

    # ── 3. sector: meta, errors 제외 (spec §4-2) ────────────────
    sector = None
    if sector_payload:
        sector = {
            k: v
            for k, v in sector_payload.items()
            if k not in ("meta", "errors")
        }

    # ── 4. sentiment (팀원 미구현, null 유지) ─────────────────────
    sentiment = sentiment_payload

    # ── 5. news_events (현재 미구현 → 빈 구조체) ───────────────────
    news_events = {
        "news_available":      False,
        "recent_news":         [],
        "recent_disclosures":  [],
    }

    return {
        "topic":      f"{ticker_name}({ticker}) 지금 매수해도 되나?",
        "topic_type": topic_type,
        "technical":  technical,
        "macro":      macro,
        "sector":     sector,
        "sentiment":  sentiment,
        "news_events": news_events,
    }
