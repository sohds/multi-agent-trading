"""
Phase 0 — 백테스팅 사전 검증

3가지 검증을 순차 실행:
  1. gpt-5.4-mini의 temperature 파라미터 지원 여부 확인
  2. pykrx 과거 OHLCV 조회(as_of) 동작 확인
  3. GT 라벨 분포 사전 산출 (4종목 × 24개월 × N=5/10/20)

산출물:
  - bull-bear/backtest/data/gt_labels.json     (gitignore — 재생성 가능)
  - bull-bear/backtest/result/phase0_validation/report.md  (커밋)

실행:
  ../../.venv_bullbear/bin/python phase0_validate.py
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from pykrx import stock

load_dotenv(find_dotenv())

BACKTEST_ROOT = Path(__file__).parent
DATA_DIR   = BACKTEST_ROOT / "data"
RESULT_DIR = BACKTEST_ROOT / "result" / "phase0_validation"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

# 테스트 대상
TICKERS = {
    "005930": "삼성전자",
    "005380": "현대차",
    "105560": "KB금융",
    "207940": "삼성바이오로직스",
}

# 테스트 기간
TEST_START = "20240101"
TEST_END   = "20251231"
HORIZONS   = [5, 10, 20]
NEUTRAL_THRESHOLD = 0.01  # |변화율| < 1%면 neutral


# ─────────────────────────────────────────────────────────────
# Test 1 — temperature 파라미터 지원 여부
# ─────────────────────────────────────────────────────────────

def test_temperature_support() -> dict:
    """gpt-5.4-mini가 temperature 파라미터를 지원하는지 확인"""
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"ok": False, "error": "OPENAI_API_KEY 미설정"}

    client = OpenAI(api_key=api_key)
    model  = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

    result = {"model": model, "with_temperature_0": None, "without_temperature": None}

    # (a) temperature=0 시도
    try:
        client.chat.completions.create(
            model=model,
            max_completion_tokens=20,
            temperature=0.0,
            messages=[{"role": "user", "content": "Reply with only: OK"}],
        )
        result["with_temperature_0"] = "지원"
    except Exception as e:
        result["with_temperature_0"] = f"미지원 — {type(e).__name__}: {str(e)[:200]}"

    # (b) temperature 미전달 (기본값)
    try:
        resp = client.chat.completions.create(
            model=model,
            max_completion_tokens=20,
            messages=[{"role": "user", "content": "Reply with only: OK"}],
        )
        result["without_temperature"] = f"동작 — 응답: {resp.choices[0].message.content[:50]}"
    except Exception as e:
        result["without_temperature"] = f"실패 — {type(e).__name__}: {str(e)[:200]}"

    result["ok"] = "동작" in (result["without_temperature"] or "")
    return result


# ─────────────────────────────────────────────────────────────
# Test 2 — pykrx 과거 OHLCV 조회 동작 확인
# ─────────────────────────────────────────────────────────────

def test_pykrx_as_of() -> dict:
    """as_of=2024-01-15로 지정했을 때 정상 조회 여부"""
    target_end = "20240115"
    target_start = "20231201"

    try:
        df = stock.get_market_ohlcv(target_start, target_end, "005930")
        if df is None or df.empty:
            return {"ok": False, "error": "DataFrame 비어 있음"}

        last_date = df.index[-1].strftime("%Y-%m-%d")
        last_close = float(df["종가"].iloc[-1])

        return {
            "ok": True,
            "rows": len(df),
            "last_date": last_date,
            "last_close": last_close,
            "lookahead_check": last_date <= "2024-01-15",
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ─────────────────────────────────────────────────────────────
# Test 3 — GT 라벨 분포 사전 산출
# ─────────────────────────────────────────────────────────────

def _label(close_now: float, close_future: float, threshold: float) -> str:
    pct = (close_future - close_now) / close_now
    if abs(pct) < threshold:
        return "neutral"
    return "bullish" if pct > 0 else "bearish"


def _monthly_first_dates(start: str, end: str) -> list[str]:
    """시작~종료 사이 매월 1일 (YYYYMMDD) 리스트"""
    dates = []
    d = datetime.strptime(start, "%Y%m%d")
    end_d = datetime.strptime(end, "%Y%m%d")
    while d <= end_d:
        dates.append(d.strftime("%Y%m%d"))
        # 다음 달 1일
        if d.month == 12:
            d = d.replace(year=d.year + 1, month=1, day=1)
        else:
            d = d.replace(month=d.month + 1, day=1)
    return dates


def build_gt_labels() -> dict:
    """4종목 × 매월 1일 × N=5/10/20 라벨 산출"""
    target_dates = _monthly_first_dates(TEST_START, TEST_END)

    # 각 종목별로 충분히 넓은 범위의 OHLCV를 한 번에 받음
    # (TEST_END + 50거래일 여유 ≈ 70 calendar days)
    fetch_start = TEST_START
    fetch_end_dt = datetime.strptime(TEST_END, "%Y%m%d") + timedelta(days=70)
    fetch_end = fetch_end_dt.strftime("%Y%m%d")

    all_records = []
    distribution = {}  # ticker → N → {bullish, bearish, neutral}

    for ticker, name in TICKERS.items():
        print(f"  [{ticker} {name}] OHLCV 수집 중...")
        df = stock.get_market_ohlcv(fetch_start, fetch_end, ticker)
        if df is None or df.empty:
            print(f"    ❌ 데이터 비어 있음")
            continue

        df.index = pd.to_datetime(df.index)
        trading_days = df.index.tolist()

        distribution[ticker] = {N: {"bullish": 0, "bearish": 0, "neutral": 0} for N in HORIZONS}

        for target_str in target_dates:
            target = datetime.strptime(target_str, "%Y%m%d")
            # target 이상의 첫 거래일 찾기
            future_days = [d for d in trading_days if d >= target]
            if not future_days:
                continue
            d0 = future_days[0]
            d0_idx = trading_days.index(d0)
            close_d0 = float(df["종가"].loc[d0])

            for N in HORIZONS:
                if d0_idx + N >= len(trading_days):
                    continue  # 미래 데이터 부족
                d_n = trading_days[d0_idx + N]
                close_dn = float(df["종가"].loc[d_n])
                label = _label(close_d0, close_dn, NEUTRAL_THRESHOLD)

                distribution[ticker][N][label] += 1
                all_records.append({
                    "ticker":     ticker,
                    "name":       name,
                    "as_of":      d0.strftime("%Y-%m-%d"),
                    "horizon":    N,
                    "close_now":  close_d0,
                    "close_future": close_dn,
                    "pct_change": round((close_dn - close_d0) / close_d0, 4),
                    "label":      label,
                })

    return {"records": all_records, "distribution": distribution}


# ─────────────────────────────────────────────────────────────
# 보고서 생성
# ─────────────────────────────────────────────────────────────

def _format_distribution(distribution: dict) -> str:
    lines = ["| 종목 | N | bullish | bearish | neutral | 합계 |", "|---|---|---|---|---|---|"]
    for ticker, by_n in distribution.items():
        for N, counts in by_n.items():
            total = sum(counts.values())
            lines.append(
                f"| {ticker} {TICKERS[ticker]} | {N} | "
                f"{counts['bullish']} | {counts['bearish']} | {counts['neutral']} | {total} |"
            )
    return "\n".join(lines)


def _aggregate_by_horizon(distribution: dict) -> str:
    by_n = {N: {"bullish": 0, "bearish": 0, "neutral": 0} for N in HORIZONS}
    for ticker_dist in distribution.values():
        for N, counts in ticker_dist.items():
            for k, v in counts.items():
                by_n[N][k] += v

    lines = ["| N | bullish | bearish | neutral | bullish 비율 | bearish 비율 |",
             "|---|---|---|---|---|---|"]
    for N, counts in by_n.items():
        total = sum(counts.values())
        if total == 0:
            continue
        b_pct = counts["bullish"] / total * 100
        be_pct = counts["bearish"] / total * 100
        lines.append(
            f"| {N} | {counts['bullish']} | {counts['bearish']} | {counts['neutral']} | "
            f"{b_pct:.1f}% | {be_pct:.1f}% |"
        )
    return "\n".join(lines)


def _bias_judgement(distribution: dict) -> str:
    """bullish/bearish 편향 정도 진단"""
    by_n = {N: {"bullish": 0, "bearish": 0, "neutral": 0} for N in HORIZONS}
    for ticker_dist in distribution.values():
        for N, counts in ticker_dist.items():
            for k, v in counts.items():
                by_n[N][k] += v

    lines = []
    for N, counts in by_n.items():
        total = sum(counts.values())
        if total == 0:
            continue
        b_pct = counts["bullish"] / total
        be_pct = counts["bearish"] / total
        max_class = max(b_pct, be_pct)
        if max_class > 0.65:
            verdict = "🔴 심한 편향 — 기간 조정 또는 Balanced Accuracy 필수"
        elif max_class > 0.55:
            verdict = "🟡 약한 편향 — Balanced Accuracy 권장"
        else:
            verdict = "🟢 균형 — 단순 적중률 사용 가능"
        lines.append(f"- N={N}: {verdict} (bullish={b_pct:.1%}, bearish={be_pct:.1%})")
    return "\n".join(lines)


def write_report(t1: dict, t2: dict, t3: dict) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULT_DIR / f"report_{ts}.md"

    bias_md = _bias_judgement(t3["distribution"])

    body = f"""# Phase 0 — 사전 검증 보고서

**실행 일시**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**테스트 기간**: {TEST_START[:4]}-{TEST_START[4:6]}-{TEST_START[6:]} ~ {TEST_END[:4]}-{TEST_END[4:6]}-{TEST_END[6:]}
**테스트 종목**: {", ".join(f"{k}({v})" for k, v in TICKERS.items())}

---

## Test 1 — gpt-5.4-mini temperature 파라미터 지원

- **모델**: `{t1.get('model')}`
- **temperature=0 호출**: {t1.get('with_temperature_0')}
- **temperature 미전달 호출**: {t1.get('without_temperature')}

**결론**: {"✅ temperature 사용 가능" if "지원" in str(t1.get("with_temperature_0", "")) else "⚠️ temperature 미지원 — LLM 비결정성 대응 방안 필요 (예: 반복 실행 후 평균)"}

---

## Test 2 — pykrx 과거 OHLCV 조회 (as_of=2024-01-15)

- **결과**: {"✅ 정상" if t2.get("ok") else "❌ 실패"}
- **수집 행 수**: {t2.get('rows', 'N/A')}
- **마지막 날짜**: {t2.get('last_date', 'N/A')}
- **마지막 종가**: {t2.get('last_close', 'N/A')}
- **룩-어헤드 차단 확인**: {"✅ 안전" if t2.get('lookahead_check') else "❌ 미래 데이터 포함됨"}
{f"- **에러**: {t2.get('error')}" if not t2.get("ok") else ""}

---

## Test 3 — GT 라벨 분포 사전 산출

총 {len(t3["records"])} 레이블 생성됨.

### 종목별 × N별 분포

{_format_distribution(t3["distribution"])}

### N별 합계 (4종목 통합)

{_aggregate_by_horizon(t3["distribution"])}

### 편향 진단

{bias_md}

---

## 다음 단계

- temperature 결과에 따라 Phase 1에서 재현성 전략 결정
- 편향이 🔴/🟡로 나오면 Balanced Accuracy를 주 지표로 사용
- 라벨 데이터는 `data/gt_labels.json`에 저장 (Phase 1+에서 재사용)
"""

    path.write_text(body, encoding="utf-8")
    return path


# ─────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Phase 0 — 백테스팅 사전 검증")
    print("=" * 60)

    print("\n[Test 1] gpt-5.4-mini temperature 파라미터 지원 확인 중...")
    t1 = test_temperature_support()
    print(f"  → temperature=0: {t1.get('with_temperature_0')}")
    print(f"  → 기본 호출:    {t1.get('without_temperature')}")

    print("\n[Test 2] pykrx 과거 OHLCV 조회 검증 중...")
    t2 = test_pykrx_as_of()
    print(f"  → 결과: {'OK' if t2.get('ok') else 'FAIL'} (last={t2.get('last_date')})")

    print("\n[Test 3] GT 라벨 분포 산출 중...")
    t3 = build_gt_labels()
    print(f"  → 총 {len(t3['records'])} 레이블 생성")

    # 라벨 저장 (gitignore)
    labels_path = DATA_DIR / "gt_labels.json"
    labels_path.write_text(
        json.dumps(t3, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )
    print(f"  → 저장: {labels_path}")

    # 보고서 저장 (커밋 대상)
    report_path = write_report(t1, t2, t3)
    print(f"\n[보고서] {report_path}")
    print("\n[완료]")


if __name__ == "__main__":
    main()
