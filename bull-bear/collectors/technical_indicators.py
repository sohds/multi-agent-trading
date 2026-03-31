"""
기술적 지표 수집 모듈
pykrx OHLCV 데이터 기반으로 기술적 지표를 계산합니다.

[출력 위치]
불/베어 공통 입력 패키지의 `technical` 필드 (agent_interface_spec.md §5)

[라이브러리]
- pykrx  : OHLCV 데이터 수집
- pandas_ta : 기술적 지표 계산 (TA-Lib C 의존성 없이 순수 Python)

[지표 목록]
- 이동평균선 (MA 5/20/60/120/200)
- 골든크로스 / 데드크로스 (20일선 × 60일선)
- RSI 14
- MACD 신호 레이블
- 볼린저 밴드 위치 레이블
- 이격도 (20일 기준)
- 거래량 변화율 (최근 5일 평균 / 직전 5일 평균)
- 거래량 급등 여부
- 지지/저항 수준 (최근 20일 고저가 기반)
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import pandas as pd
from pykrx import stock

try:
    import pandas_ta as ta
    _HAS_PANDAS_TA = True
except ImportError:
    _HAS_PANDAS_TA = False


# ─────────────────────────────────────────────────────────────
# OHLCV 수집
# ─────────────────────────────────────────────────────────────

def _get_ohlcv(ticker: str, days: int = 300) -> Optional[pd.DataFrame]:
    """
    pykrx로 OHLCV 수집.
    MA200 계산에 최소 200 거래일이 필요하므로 calendar 기준 300일로 요청.

    Returns:
        DataFrame (index=날짜, columns=[시가, 고가, 저가, 종가, 거래량, ...])
        또는 None
    """
    today = datetime.today().strftime("%Y%m%d")
    start = (datetime.today() - timedelta(days=days)).strftime("%Y%m%d")
    try:
        df = stock.get_market_ohlcv(start, today, ticker)
        if df is None or df.empty:
            return None
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# 보조 계산 함수
# ─────────────────────────────────────────────────────────────

def _ma(close: pd.Series, n: int) -> Optional[float]:
    if len(close) < n:
        return None
    return round(float(close.rolling(n).mean().iloc[-1]), 0)


def _cross_signals(close: pd.Series) -> Tuple[bool, bool]:
    """
    20일선과 60일선의 골든/데드크로스 감지.

    조건:
      - 골든크로스: 전일 MA20 < MA60  AND  당일 MA20 >= MA60
      - 데드크로스: 전일 MA20 > MA60  AND  당일 MA20 <= MA60

    Returns:
        (golden_cross, dead_cross)
    """
    if len(close) < 61:
        return False, False

    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()

    prev_diff = ma20.iloc[-2] - ma60.iloc[-2]
    curr_diff = ma20.iloc[-1] - ma60.iloc[-1]

    golden = bool(prev_diff < 0 and curr_diff >= 0)
    dead   = bool(prev_diff > 0 and curr_diff <= 0)
    return golden, dead


def _macd_label(close: pd.Series) -> str:
    """
    MACD(12,26,9) 신호 레이블.

    반환값:
      "bullish_crossover"  : MACD가 시그널선을 상향 돌파 (당일)
      "bearish_crossover"  : MACD가 시그널선을 하향 돌파 (당일)
      "bullish"            : MACD > 시그널 (돌파 이후 유지)
      "bearish"            : MACD < 시그널
      "데이터 부족"          : pandas_ta 미설치 또는 데이터 부족
    """
    if not _HAS_PANDAS_TA or len(close) < 35:
        return "데이터 부족"

    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    if macd_df is None or macd_df.empty or len(macd_df) < 2:
        return "데이터 부족"

    # pandas_ta 컬럼명: MACD_12_26_9 / MACDs_12_26_9 / MACDh_12_26_9
    macd_col   = next((c for c in macd_df.columns if c.startswith("MACD_")), None)
    signal_col = next((c for c in macd_df.columns if c.startswith("MACDs_")), None)
    if not macd_col or not signal_col:
        return "데이터 부족"

    m_now  = float(macd_df[macd_col].iloc[-1])
    s_now  = float(macd_df[signal_col].iloc[-1])
    m_prev = float(macd_df[macd_col].iloc[-2])
    s_prev = float(macd_df[signal_col].iloc[-2])

    if m_prev < s_prev and m_now >= s_now:
        return "bullish_crossover"
    if m_prev > s_prev and m_now <= s_now:
        return "bearish_crossover"
    return "bullish" if m_now > s_now else "bearish"


def _bollinger_label(close: pd.Series, price: float) -> str:
    """
    볼린저 밴드(20, 2σ) 내 현재 위치 레이블.

    반환값:
      "upper_band_near"  : 밴드 상단 80% 이상 위치
      "lower_band_near"  : 밴드 하단 20% 이하 위치
      "middle"           : 중간 구간
      "데이터 부족"        : pandas_ta 미설치 또는 데이터 부족
    """
    if not _HAS_PANDAS_TA or len(close) < 20:
        return "데이터 부족"

    bb = ta.bbands(close, length=20, std=2)
    if bb is None or bb.empty:
        return "데이터 부족"

    upper_col  = next((c for c in bb.columns if c.startswith("BBU_")), None)
    lower_col  = next((c for c in bb.columns if c.startswith("BBL_")), None)
    if not upper_col or not lower_col:
        return "데이터 부족"

    upper = float(bb[upper_col].iloc[-1])
    lower = float(bb[lower_col].iloc[-1])
    width = upper - lower
    if width == 0:
        return "middle"

    pos = (price - lower) / width  # 0.0(하단) ~ 1.0(상단)
    if pos >= 0.8:
        return "upper_band_near"
    if pos <= 0.2:
        return "lower_band_near"
    return "middle"


def _support_resistance(df: pd.DataFrame, window: int = 20) -> Tuple[float, float]:
    """
    최근 N일 고저가 기반 지지/저항 수준.

    지지  : 최근 window일 최저가
    저항  : 최근 window일 최고가

    단순 고저가이므로 실제 캔들 패턴 분석은 별도 구현 필요.
    """
    recent = df.tail(window)
    support    = round(float(recent["저가"].min()), 0)
    resistance = round(float(recent["고가"].max()), 0)
    return support, resistance


def _volume_stats(volume: pd.Series) -> Tuple[Optional[float], bool]:
    """
    거래량 변화율 및 급등 여부.

    변화율 : (최근 5일 평균 / 직전 5일 평균) - 1
    급등   : 당일 거래량 > 20일 평균의 2배

    Returns:
        (volume_change_5d, volume_spike)
    """
    change = None
    spike  = False

    if len(volume) >= 10:
        recent_5d = volume.iloc[-5:].mean()
        prev_5d   = volume.iloc[-10:-5].mean()
        if prev_5d > 0:
            change = round(float((recent_5d / prev_5d) - 1), 2)

    if len(volume) >= 20:
        avg_20d = volume.iloc[-20:].mean()
        spike = bool(volume.iloc[-1] > avg_20d * 2)

    return change, spike


# ─────────────────────────────────────────────────────────────
# 공개 API
# ─────────────────────────────────────────────────────────────

def get_technical_indicators(ticker: str, ticker_name: str) -> dict:
    """
    기술적 지표 통합 수집 (불/베어 입력 패키지 `technical` 필드)

    Args:
        ticker      : 종목 코드 (예: "005930")
        ticker_name : 종목명   (예: "삼성전자")

    Returns:
        dict: {
            "ticker", "name", "date", "price",
            "ma_5", "ma_20", "ma_60", "ma_120", "ma_200",
            "golden_cross_20_60" : bool  — 당일 골든크로스 발생 여부
            "dead_cross_20_60"   : bool  — 당일 데드크로스 발생 여부
            "rsi_14"             : float — 14일 RSI (0~100)
            "macd_signal"        : str   — "bullish_crossover" | "bearish_crossover" | "bullish" | "bearish"
            "bollinger_position" : str   — "upper_band_near" | "middle" | "lower_band_near"
            "disparity_20"       : float — 20일 이격도 (price/MA20 × 100)
            "volume_change_5d"   : float — 최근 5일 평균 거래량 변화율 (소수)
            "volume_spike"       : bool  — 당일 거래량 > 20일 평균의 2배
            "support_level"      : float — 최근 20일 저가 기반 지지선
            "resistance_level"   : float — 최근 20일 고가 기반 저항선
        }
        또는 {"error": str}
    """
    df = _get_ohlcv(ticker, days=300)
    if df is None or len(df) < 20:
        return {"error": f"OHLCV 데이터 부족 (ticker={ticker})"}

    close  = df["종가"]
    volume = df["거래량"]
    price  = round(float(close.iloc[-1]), 0)
    date   = df.index[-1].strftime("%Y-%m-%d")

    # ── 이동평균선 ─────────────────────────────────────
    ma_5   = _ma(close, 5)
    ma_20  = _ma(close, 20)
    ma_60  = _ma(close, 60)
    ma_120 = _ma(close, 120)
    ma_200 = _ma(close, 200)

    # ── 골든/데드크로스 ────────────────────────────────
    golden_cross, dead_cross = _cross_signals(close)

    # ── RSI ───────────────────────────────────────────
    rsi_14 = None
    if _HAS_PANDAS_TA and len(close) >= 15:
        rsi_series = ta.rsi(close, length=14)
        if rsi_series is not None and not rsi_series.empty:
            rsi_14 = round(float(rsi_series.iloc[-1]), 1)

    # ── MACD ──────────────────────────────────────────
    macd_signal = _macd_label(close)

    # ── 볼린저 밴드 ────────────────────────────────────
    bollinger_position = _bollinger_label(close, price)

    # ── 이격도 (20일) ──────────────────────────────────
    disparity_20 = round(price / ma_20 * 100, 1) if ma_20 else None

    # ── 거래량 ────────────────────────────────────────
    volume_change_5d, volume_spike = _volume_stats(volume)

    # ── 지지/저항 ──────────────────────────────────────
    support_level, resistance_level = _support_resistance(df, window=20)

    return {
        "ticker":             ticker,
        "name":               ticker_name,
        "date":               date,
        "price":              price,
        "ma_5":               ma_5,
        "ma_20":              ma_20,
        "ma_60":              ma_60,
        "ma_120":             ma_120,
        "ma_200":             ma_200,
        "golden_cross_20_60": golden_cross,
        "dead_cross_20_60":   dead_cross,
        "rsi_14":             rsi_14,
        "macd_signal":        macd_signal,
        "bollinger_position": bollinger_position,
        "disparity_20":       disparity_20,
        "volume_change_5d":   volume_change_5d,
        "volume_spike":       volume_spike,
        "support_level":      support_level,
        "resistance_level":   resistance_level,
    }
