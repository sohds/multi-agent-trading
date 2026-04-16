"""
불/베어 에이전트 실행 진입점

실행:
    python bull_bear_main.py

환경변수 (.env):
    ANTHROPIC_API_KEY   필수
    TARGET_TICKER       분석 종목 코드      (기본: 005930)
    TARGET_NAME         분석 종목명         (기본: 삼성전자)
    SECTOR_ETF_TICKER   섹터 ETF 코드       (기본: 091160)
    DEBATE_ROUNDS       토론 라운드 수       (기본: 1)
    OPENAI_MODEL        사용할 OpenAI 모델  (기본: gpt-4o)
    SAVE_JSON           결과 저장 여부       (기본: true)
    OUTPUT_DIR          JSON 저장 경로       (기본: output)
    USE_MACRO           매크로 에이전트 실행  (기본: true)
    USE_SECTOR          섹터 에이전트 실행   (기본: true)
    USE_MARKET          시장심리 에이전트 실행 (기본: true)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# ── sys.path 설정 ─────────────────────────────────────────────
BULL_BEAR_ROOT = Path(__file__).parent
PROJECT_ROOT   = BULL_BEAR_ROOT.parent

sys.path.insert(0, str(BULL_BEAR_ROOT))           # package_builder, agents
sys.path.insert(0, str(PROJECT_ROOT / "macro"))   # macro_agents.macro_agent
sys.path.insert(0, str(PROJECT_ROOT / "sector"))  # sector_agents.sector_agent
sys.path.insert(0, str(PROJECT_ROOT / "market"))  # market_collectors.sentiment_collector

from package_builder import build_input_package  # noqa: E402
from agents.bull_agent import run_bull_agent     # noqa: E402
from agents.bear_agent import run_bear_agent     # noqa: E402


# ── 설정 ─────────────────────────────────────────────────────
TICKER       = os.getenv("TARGET_TICKER", "005930")
TICKER_NAME  = os.getenv("TARGET_NAME",   "삼성전자")
SECTOR_ETF   = os.getenv("SECTOR_ETF_TICKER", "091160")
ROUNDS       = int(os.getenv("DEBATE_ROUNDS", "1"))
MODEL        = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
SAVE_JSON    = os.getenv("SAVE_JSON", "true").lower() == "true"
OUTPUT_DIR   = os.getenv("OUTPUT_DIR", "output")
USE_MACRO    = os.getenv("USE_MACRO",   "true").lower() == "true"
USE_SECTOR   = os.getenv("USE_SECTOR", "true").lower() == "true"
USE_MARKET   = os.getenv("USE_MARKET", "true").lower() == "true"


# ── 외부 에이전트 실행 (실패 시 None 반환) ─────────────────────

def _run_macro() -> dict | None:
    try:
        from macro_agents.macro_agent import run_macro_agent
        print("[macro] 매크로 에이전트 실행 중...")
        result = run_macro_agent()
        if result.get("errors"):
            print(f"[macro] 경고: {result['errors']}")
        return result
    except Exception as e:
        print(f"[macro] 건너뜀 — {e}")
        return None


def _run_market() -> dict | None:
    """market agent 실행 후 스펙 §3 sentiment 포맷으로 변환"""
    try:
        from market_collectors.sentiment_collector import MarketSentimentCollector
        print("[market] 시장심리 에이전트 실행 중...")
        raw = MarketSentimentCollector().analyze_sentiment()
        # market agent 출력(analysis.* / raw_data.*)을 스펙 §3 flat 구조로 변환
        return {
            "sentiment_label": raw["analysis"]["sentiment_label"],
            "sentiment_score": raw["analysis"]["sentiment_score"],
            "confidence":      raw["analysis"]["confidence"],
            "risk_signal":     raw["analysis"]["risk_signal"],
            "vkospi":          raw["raw_data"]["vkospi"],
            "foreign_flow":    raw["raw_data"]["foreign_flow"],
            "market_momentum": raw["raw_data"]["market_momentum"],
            "reason":          raw["reason"],
        }
    except Exception as e:
        print(f"[market] 건너뜀 — {e}")
        return None


def _run_sector() -> dict | None:
    try:
        from sector_agents.sector_agent import run_sector_agent
        print("[sector] 섹터 에이전트 실행 중...")
        result = run_sector_agent(TICKER, TICKER_NAME, SECTOR_ETF)
        if result.get("errors"):
            print(f"[sector] 경고: {result['errors']}")
        return result
    except Exception as e:
        print(f"[sector] 건너뜀 — {e}")
        return None


# ── 결과 출력 ─────────────────────────────────────────────────

def _print_result(label: str, result: dict) -> None:
    bar = "─" * 60
    print(f"\n{bar}")
    print(f"  {label}")
    print(bar)

    if "error" in result:
        print(f"  [오류] {result['error']}")
        if "raw_response" in result:
            print(f"  [원문] {result['raw_response'][:300]}")
        return

    stance     = result.get("stance", "?")
    confidence = result.get("confidence", 0)
    summary    = result.get("summary", "")
    rebuttal   = result.get("rebuttal")
    arguments  = result.get("arguments", [])

    print(f"  스탠스:    {stance.upper()}")
    print(f"  확신도:    {confidence:.2f}")
    print(f"  요약:      {summary}")

    print("\n  [논거]")
    for i, arg in enumerate(arguments, 1):
        print(f"    {i}. {arg.get('claim')}")
        print(f"       근거: {arg.get('data_ref')}")

    if rebuttal:
        print(f"\n  [반박] {rebuttal}")


# ── 저장 ─────────────────────────────────────────────────────

def _save(payload: dict) -> None:
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"debate_{TICKER}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[저장] {path}")


# ── 메인 ─────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print(f"  불/베어 토론 에이전트 — {TICKER_NAME}({TICKER})")
    print(f"  모델: {MODEL}  |  라운드: {ROUNDS}")
    print("=" * 60)

    # 외부 에이전트 수집
    macro_payload     = _run_macro()   if USE_MACRO   else None
    sector_payload    = _run_sector()  if USE_SECTOR  else None
    sentiment_payload = _run_market()  if USE_MARKET  else None

    # 입력 패키지 조립
    print("\n[package] 입력 패키지 조립 중...")
    pkg = build_input_package(
        ticker=TICKER,
        ticker_name=TICKER_NAME,
        sector_payload=sector_payload,
        macro_payload=macro_payload,
        sentiment_payload=sentiment_payload,
    )

    bull_result = None
    bear_result = None

    for rnd in range(1, ROUNDS + 1):
        print(f"\n{'━' * 60}")
        print(f"  라운드 {rnd} / {ROUNDS}")
        print(f"{'━' * 60}")

        print("[bull] 논거 생성 중...")
        bull_result = run_bull_agent(pkg, bear_argument=bear_result, model=MODEL)
        _print_result(f"BULL 에이전트 (라운드 {rnd})", bull_result)

        print("\n[bear] 논거 생성 중...")
        bear_result = run_bear_agent(pkg, bull_argument=bull_result, model=MODEL)
        _print_result(f"BEAR 에이전트 (라운드 {rnd})", bear_result)

    # 저장
    output_payload = {
        "meta": {
            "ticker":     TICKER,
            "name":       TICKER_NAME,
            "model":      MODEL,
            "rounds":     ROUNDS,
            "as_of":      datetime.now().strftime("%Y-%m-%d %H:%M"),
            "macro_used":     macro_payload is not None,
            "sector_used":    sector_payload is not None,
            "sentiment_used": sentiment_payload is not None,
        },
        "input_package": pkg,
        "bull": bull_result,
        "bear": bear_result,
    }

    if SAVE_JSON:
        _save(output_payload)

    print("\n[완료]")


if __name__ == "__main__":
    main()
