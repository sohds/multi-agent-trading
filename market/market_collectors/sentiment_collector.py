import requests
import yfinance as yf
from pykrx import stock
from datetime import datetime, timedelta

KRX_AUTH_KEY = "74D1B99DFBF345BBA3FB4476510A4BED4C78D13A"

class MarketSentimentCollector:
    def __init__(self):
        self.kospi_ticker = "^KS11"
        self.vkospi_url = "https://data-dbg.krx.co.kr/svc/apis/idx/drvprod_dd_trd"

    def _fetch_vkospi(self, date_str: str) -> dict:
        try:
            resp = requests.get(
                self.vkospi_url,
                params={"AUTH_KEY": KRX_AUTH_KEY, "basDd": date_str},
                timeout=10
            )
            items = resp.json().get("OutBlock_1", [])
            vkospi_item = next(
                (item for item in items if "변동성" in item.get("IDX_NM", "")),
                None
            )
            if not vkospi_item:
                return {"value": None, "change": None, "change_rate": None}

            return {
                "value":       float(vkospi_item["CLSPRC_IDX"]),
                "change":      float(vkospi_item["CMPPREVDD_IDX"]),
                "change_rate": float(vkospi_item["FLUC_RT"]),
            }
        except Exception as e:
            print(f"❌ VKOSPI 조회 실패: {e}")
            return {"value": None, "change": None, "change_rate": None}

    def fetch_all_data(self):
        end_date   = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

        # --- 외국인 수급 ---
        df_investor = stock.get_market_trading_value_by_investor(
            start_date, end_date, "KOSPI"
        )
        if df_investor is None or df_investor.empty:
            net_buy, trend = 0, "데이터 없음"
        else:
            raw_value = float(df_investor.loc['외국인', '순매수'])
            net_buy   = round(raw_value / 1e8)
            trend     = "순매수" if raw_value > 0 else "순매도"

        # --- 코스피 ---
        kospi_df = yf.download(self.kospi_ticker, period="7d", progress=False)
        if not kospi_df.empty:
            curr_kospi   = kospi_df['Close'].iloc[-1].item()
            prev_kospi   = kospi_df['Close'].iloc[0].item()
            kospi_change = (curr_kospi - prev_kospi) / prev_kospi
            market_trend = "상승" if kospi_change > 0 else "하락"
        else:
            kospi_change, market_trend = 0.0, "정체"

        # --- VKOSPI ---
        vkospi = self._fetch_vkospi(end_date)

        return {
            "vkospi": vkospi,
            "foreign_flow": {"net_buy": net_buy, "trend": trend},
            "kospi_change_rate": kospi_change,
            "market_trend": market_trend
        }


if __name__ == "__main__":
    collector = MarketSentimentCollector()
    result = collector.fetch_all_data()

    print(f"VKOSPI: {result['vkospi']['value']} ({result['vkospi']['change_rate']}%)")
    print(f"외국인 순매수: {result['foreign_flow']['net_buy']:,} 억원 ({result['foreign_flow']['trend']})")
    print(f"코스피 변화율: {result['kospi_change_rate']:.2%}")
    print(f"시장 트렌드:   {result['market_trend']}")