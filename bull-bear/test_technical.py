"""
기술적 지표 수집 모듈 동작 확인 스크립트
실행: python test_technical.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from collectors.technical_indicators import get_technical_indicators

TICKER      = "005930"
TICKER_NAME = "삼성전자"

SEP  = "=" * 60
SEP2 = "-" * 60

def main():
    print(f"\n{SEP}")
    print(f"  기술적 지표 수집 테스트 — {TICKER_NAME} ({TICKER})")
    print(SEP)

    result = get_technical_indicators(TICKER, TICKER_NAME)

    if "error" in result:
        print(f"  [오류] {result['error']}")
        return

    print(f"\n  기준일 : {result['date']}")
    print(f"  현재가 : {result['price']:,.0f}원")

    print(f"\n{SEP2}")
    print("  이동평균선")
    print(SEP2)
    for key in ["ma_5", "ma_20", "ma_60", "ma_120", "ma_200"]:
        val = result.get(key)
        label = f"{key.upper():<8}"
        print(f"  {label} : {val:,.0f}원" if val else f"  {label} : N/A")

    print(f"\n{SEP2}")
    print("  크로스 · 추세 신호")
    print(SEP2)
    print(f"  골든크로스(20×60)  : {'✅ 발생' if result['golden_cross_20_60'] else '—'}")
    print(f"  데드크로스(20×60)  : {'⚠️  발생' if result['dead_cross_20_60']  else '—'}")
    print(f"  MACD 신호          : {result['macd_signal']}")
    print(f"  볼린저 밴드 위치   : {result['bollinger_position']}")

    print(f"\n{SEP2}")
    print("  모멘텀 지표")
    print(SEP2)
    rsi = result.get("rsi_14")
    print(f"  RSI 14             : {rsi:.1f}" if rsi else "  RSI 14             : N/A")
    d20 = result.get("disparity_20")
    print(f"  이격도 (20일)      : {d20:.1f}%" if d20 else "  이격도 (20일)      : N/A")

    print(f"\n{SEP2}")
    print("  거래량")
    print(SEP2)
    vc = result.get("volume_change_5d")
    vc_str = f"{vc:+.1%}" if vc is not None else "N/A"
    print(f"  5일 거래량 변화율  : {vc_str}")
    print(f"  거래량 급등        : {'⚠️  있음' if result['volume_spike'] else '—'}")

    print(f"\n{SEP2}")
    print("  지지 / 저항")
    print(SEP2)
    print(f"  지지선  (20일 저가): {result['support_level']:,.0f}원")
    print(f"  저항선  (20일 고가): {result['resistance_level']:,.0f}원")

    print(f"\n{SEP}\n")

if __name__ == "__main__":
    main()
