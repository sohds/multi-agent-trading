"""
백테스트 실행기 (Phase 1+)

흐름:
  1. data/gt_labels.json에서 GT 라벨 로드
  2. 케이스 필터링 (--ticker, --track 옵션)
  3. 각 케이스에 대해:
     - technical 지표 계산 (as_of 주입)
     - 마스킹 적용 (트랙 A) 또는 미적용 (트랙 C)
     - bull/bear 에이전트 호출 (ROUNDS=1)
     - 예측 방향 분류 (conf_diff 임계값 ±0.05)
  4. 결과 JSON 저장 (result/<phase>/<timestamp>.json)
  5. 기본 통계 출력 (적중률, Balanced Accuracy)

실행 예:
  ../../.venv_bullbear/bin/python backtest_runner.py --phase=1 --ticker=005930 --track=A
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# ── sys.path: bull-bear 루트와 backtest 둘 다 ──────────────────
BACKTEST_ROOT = Path(__file__).parent
BULL_BEAR_ROOT = BACKTEST_ROOT.parent
PROJECT_ROOT  = BULL_BEAR_ROOT.parent

sys.path.insert(0, str(BULL_BEAR_ROOT))           # package_builder, agents
sys.path.insert(0, str(BACKTEST_ROOT.parent))     # backtest.masking import 경로
sys.path.insert(0, str(PROJECT_ROOT / "macro"))   # macro_agents.macro_agent

from package_builder import build_input_package    # noqa: E402
from agents.bull_agent import run_bull_agent       # noqa: E402
from agents.bear_agent import run_bear_agent       # noqa: E402

# ── 설정 ──────────────────────────────────────────────────────
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
NEUTRAL_THRESHOLD = 0.05  # |bull_conf - bear_conf| < 0.05 → neutral 예측

DATA_DIR   = BACKTEST_ROOT / "data"
RESULT_DIR = BACKTEST_ROOT / "result"

TICKER_NAMES = {
    "005930": "삼성전자",
    "005380": "현대차",
    "105560": "KB금융",
    "207940": "삼성바이오로직스",
}


# ── GT 로드 ───────────────────────────────────────────────────

def load_gt_labels() -> dict:
    path = DATA_DIR / "gt_labels.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} 없음. 먼저 phase0_validate.py를 실행하세요."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def group_cases_by_date(records: list[dict], ticker: str | None = None) -> dict:
    """records → {(ticker, as_of): {horizon: label}}"""
    cases = defaultdict(dict)
    for rec in records:
        if ticker and rec["ticker"] != ticker:
            continue
        key = (rec["ticker"], rec["as_of"])
        cases[key][rec["horizon"]] = rec["label"]
    return dict(cases)


# ── 예측 분류 ─────────────────────────────────────────────────

def classify_prediction(bull: dict, bear: dict) -> tuple[str, float]:
    """confidence 차이로 예측 방향 분류"""
    if "error" in bull or "error" in bear:
        return "error", 0.0
    bull_conf = bull.get("confidence", 0.0)
    bear_conf = bear.get("confidence", 0.0)
    diff = bull_conf - bear_conf
    if abs(diff) < NEUTRAL_THRESHOLD:
        return "neutral", diff
    return ("bullish" if diff > 0 else "bearish"), diff


# ── 메인 실행 ─────────────────────────────────────────────────

def run_case(ticker: str, ticker_name: str, as_of: str, mask: bool, macro_enabled: bool = False) -> dict:
    """단일 케이스 실행"""
    as_of_compact = as_of.replace("-", "")  # YYYY-MM-DD → YYYYMMDD
    macro_payload = None
    if macro_enabled:
        from macro_agents.macro_agent import run_macro_agent
        macro_payload = run_macro_agent(as_of=as_of_compact)

    pkg = build_input_package(
        ticker=ticker,
        ticker_name=ticker_name,
        as_of=as_of_compact,
        mask_for_backtest=mask,
        macro_payload=macro_payload,
    )

    bull = run_bull_agent(pkg, model=MODEL)
    bear = run_bear_agent(pkg, model=MODEL)

    prediction, conf_diff = classify_prediction(bull, bear)

    return {
        "ticker":       ticker,
        "as_of":        as_of,
        "prediction":   prediction,
        "conf_diff":    round(conf_diff, 4),
        "bull_conf":    bull.get("confidence"),
        "bear_conf":    bear.get("confidence"),
        "bull_summary": bull.get("summary"),
        "bear_summary": bear.get("summary"),
        "bull_error":   bull.get("error"),
        "bear_error":   bear.get("error"),
        "macro_error":  macro_payload.get("errors") if macro_payload else None,
    }


def run_backtest(
    ticker: str | None,
    track: str,
    mask_override: str | None = None,
    max_cases: int | None = None,
    macro_enabled: bool = False,
) -> dict:
    """백테스트 메인 루프"""
    gt = load_gt_labels()
    cases = group_cases_by_date(gt["records"], ticker=ticker)

    if max_cases:
        cases = dict(list(cases.items())[:max_cases])

    if mask_override is not None:
        mask = (mask_override == "on")
    else:
        mask = (track == "A")  # 기본: 트랙 A=ON, C=OFF
    print(f"\n{'='*60}")
    print(f"  백테스트 실행 — 트랙 {track} ({'마스킹 ON' if mask else '마스킹 OFF'})")
    print(f"  모델: {MODEL}")
    print(f"  Macro: {'ON' if macro_enabled else 'OFF'}")
    print(f"  케이스 수: {len(cases)}")
    print(f"{'='*60}\n")

    results = []
    for i, ((ticker_, as_of), gt_labels) in enumerate(cases.items(), 1):
        ticker_name = TICKER_NAMES.get(ticker_, ticker_)
        print(f"  [{i}/{len(cases)}] {ticker_} {ticker_name} {as_of} ...")

        case_result = run_case(ticker_, ticker_name, as_of, mask, macro_enabled=macro_enabled)
        case_result["gt_labels"] = gt_labels

        # GT와 즉시 비교
        case_result["correct"] = {
            N: (case_result["prediction"] == gt_label)
            for N, gt_label in gt_labels.items()
        }
        results.append(case_result)

        pred = case_result["prediction"]
        gt5 = gt_labels.get(5, "?")
        print(f"      예측={pred}  GT(N=5)={gt5}  conf_diff={case_result['conf_diff']:+.3f}")

    return {
        "meta": {
            "track":      track,
            "ticker":     ticker,
            "model":      MODEL,
            "macro":      macro_enabled,
            "case_count": len(cases),
            "ran_at":     datetime.now().isoformat(timespec="seconds"),
        },
        "results": results,
    }


# ── 통계 ──────────────────────────────────────────────────────

def compute_stats(results: list[dict]) -> dict:
    """방향 적중률 및 Balanced Accuracy"""
    horizons = [5, 10, 20]
    stats = {}
    for N in horizons:
        valid = [
            r for r in results
            if r["prediction"] in ("bullish", "bearish")
            and r["gt_labels"].get(N) in ("bullish", "bearish")
        ]
        if not valid:
            stats[N] = {"valid_n": 0}
            continue

        correct = sum(1 for r in valid if r["prediction"] == r["gt_labels"][N])
        accuracy = correct / len(valid)

        # Balanced accuracy: 클래스별 적중률 평균
        bull_cases = [r for r in valid if r["gt_labels"][N] == "bullish"]
        bear_cases = [r for r in valid if r["gt_labels"][N] == "bearish"]
        bull_acc = (sum(1 for r in bull_cases if r["prediction"] == "bullish")
                    / len(bull_cases)) if bull_cases else None
        bear_acc = (sum(1 for r in bear_cases if r["prediction"] == "bearish")
                    / len(bear_cases)) if bear_cases else None
        balanced = (
            (bull_acc + bear_acc) / 2
            if bull_acc is not None and bear_acc is not None
            else None
        )

        stats[N] = {
            "valid_n":          len(valid),
            "correct":          correct,
            "accuracy":         round(accuracy, 4),
            "bull_accuracy":    round(bull_acc, 4) if bull_acc is not None else None,
            "bear_accuracy":    round(bear_acc, 4) if bear_acc is not None else None,
            "balanced_accuracy": round(balanced, 4) if balanced is not None else None,
        }

    # 추가 지표
    total = len(results)
    pred_dist = defaultdict(int)
    error_count = 0
    for r in results:
        pred_dist[r["prediction"]] += 1
        if r.get("bull_error") or r.get("bear_error"):
            error_count += 1

    return {
        "by_horizon":    stats,
        "prediction_distribution": dict(pred_dist),
        "error_count":   error_count,
        "total_cases":   total,
    }


def print_stats(stats: dict, track: str):
    print(f"\n{'='*60}")
    print(f"  통계 — 트랙 {track}")
    print(f"{'='*60}")
    print(f"  총 케이스: {stats['total_cases']}, 에러: {stats['error_count']}")
    print(f"  예측 분포: {stats['prediction_distribution']}")
    print()
    print(f"  {'N':>4} | {'유효':>5} | {'적중률':>8} | {'Bull정확':>8} | {'Bear정확':>8} | {'Balanced':>8}")
    print(f"  {'-'*4} | {'-'*5} | {'-'*8} | {'-'*8} | {'-'*8} | {'-'*8}")
    for N, s in stats["by_horizon"].items():
        if not s.get("valid_n"):
            print(f"  {N:>4} | (유효 케이스 없음)")
            continue
        acc  = f"{s['accuracy']:.1%}"
        bull = f"{s['bull_accuracy']:.1%}" if s.get('bull_accuracy') is not None else "N/A"
        bear = f"{s['bear_accuracy']:.1%}" if s.get('bear_accuracy') is not None else "N/A"
        bal  = f"{s['balanced_accuracy']:.1%}" if s.get('balanced_accuracy') is not None else "N/A"
        print(f"  {N:>4} | {s['valid_n']:>5} | {acc:>8} | {bull:>8} | {bear:>8} | {bal:>8}")


# ── CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Bull-Bear 백테스트")
    parser.add_argument("--phase",  type=str, default="1", help="실행 Phase (저장 경로용, 예: 1, 2, 2-prompt)")
    parser.add_argument("--ticker", type=str, default=None, help="단일 종목 코드 (없으면 전체)")
    parser.add_argument("--track",  type=str, choices=["A", "C"], default="A",
                        help="A: Technical만 + 마스킹 ON / C: 전체 데이터 + 마스킹 OFF")
    parser.add_argument("--mask",   type=str, choices=["on", "off"], default=None,
                        help="마스킹 강제 지정 (track 기본값 무시). on/off")
    parser.add_argument("--macro",  type=str, choices=["on", "off"], default="off",
                        help="Macro payload 사용 여부. 기본 off")
    parser.add_argument("--max",    type=int, default=None, help="최대 케이스 수 제한")
    args = parser.parse_args()

    macro_enabled = args.macro == "on"
    payload = run_backtest(
        args.ticker,
        args.track,
        mask_override=args.mask,
        max_cases=args.max,
        macro_enabled=macro_enabled,
    )
    stats = compute_stats(payload["results"])
    payload["stats"] = stats

    print_stats(stats, args.track)

    # 저장 경로: result/phaseN_<track>/<timestamp>.json
    track_label = "technical_only" if args.track == "A" else "full_data"
    if args.mask == "off" and args.track == "A":
        track_label = "technical_nomask"
    if macro_enabled:
        track_label = "macro"
    out_dir = RESULT_DIR / f"phase{args.phase}_{track_label}"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"run_{ts}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n[저장] {out_path}")


if __name__ == "__main__":
    main()
