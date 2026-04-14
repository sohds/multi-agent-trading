import os
import json
import requests
import yfinance as yf
from pykrx import stock
from datetime import datetime, timedelta

# pykrx 패치 스크립트(patch_pykrx.py) 실행 후 생성되는 webio 모듈에서 세션 가져오기 시도
try:
    from pykrx.website.comm.webio import get_session
except ImportError:
    get_session = lambda: None

class MarketSentimentCollector:
    def __init__(self):
        self.kospi_ticker = "^KS11"
        self.vkospi_url = "https://data-dbg.krx.co.kr/svc/apis/idx/drvprod_dd_trd"
        # pykrx 스크래핑용 세션 (패치된 경우 로그인 유지)
        self.session = get_session() or requests.Session()

    # ----- VKOSPI 불러오기 -----
    def _fetch_vkospi(self, date_str: str) -> dict:
        auth_key = os.getenv("KRX_AUTH_KEY")
        
        if not auth_key:
            print("⚠️ 환경변수에 KRX_AUTH_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
            return {"value": 20.0, "change": 0.0, "change_rate": 0.0}

        try:
            # pykrx 세션과 무관하게 독립적인 requests 호출 (Open API용)
            resp = requests.get(
                self.vkospi_url,
                params={
                    "AUTH_KEY": auth_key, 
                    "basDd": date_str
                },
                timeout=10
            )
            
            if not resp.ok:
                print(f"❌ API HTTP 에러: {resp.status_code}")
                return {"value": 20.0, "change": 0.0, "change_rate": 0.0}

            data = resp.json()
            items = data.get("OutBlock_1", [])

            vkospi_item = next(
                (item for item in items if item.get("IDX_NM") == "코스피 200 변동성지수"), 
                None
            )

            # 주말이나 휴일이라 데이터가 없는 경우
            if not vkospi_item:
                print(f"⚠️ {date_str} 기준 VKOSPI 데이터가 비어있습니다. (주말/휴일 가능성)")
                return {"value": 20.0, "change": 0.0, "change_rate": 0.0} 

            return {
                "value": float(vkospi_item["CLSPRC_IDX"]),
                "change": float(vkospi_item["CMPPREVDD_IDX"]),
                "change_rate": float(vkospi_item["FLUC_RT"]),
            }

        except Exception as e:
            print(f"❌ VKOSPI 파싱 실패: {e}")
            return {"value": 20.0, "change": 0.0, "change_rate": 0.0}

    def analyze_sentiment(self):
        """
        sentiment_collector를 통해 출력된 지표들을 JSON 형태로 반환
        """
        # --------------------------------------------------------
        # 1. 데이터 수집
        # --------------------------------------------------------
        end_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

        # --- 외국인 수급 (pykrx) ---
        try:
            df_investor = stock.get_market_trading_value_by_investor(start_date, end_date, "KOSPI")
            if df_investor is None or df_investor.empty:
                net_buy, foreign_trend = 0, "데이터 없음"
            else:
                raw_value = float(df_investor.loc['외국인', '순매수'])
                net_buy = round(raw_value / 1e8) # 억원 단위
                foreign_trend = "순매수" if raw_value > 0 else "순매도"
        except Exception as e:
            print(f"⚠️ 외국인 수급 조회 실패: {e}")
            net_buy, foreign_trend = 0, "데이터 없음"

        # --- 코스피 (Yahoo Finance) ---
        try:
            kospi_df = yf.download(self.kospi_ticker, period="7d", progress=False)
            if not kospi_df.empty:
                # pandas DataFrame 인덱싱
                curr_kospi = float(kospi_df['Close'].iloc[-1].item())
                prev_kospi = float(kospi_df['Close'].iloc[0].item())
                
                kospi_change = (curr_kospi - prev_kospi) / prev_kospi
                market_trend = "상승" if kospi_change > 0 else "하락"
            else:
                kospi_change, market_trend = 0.0, "정체"
        except Exception as e:
            print(f"⚠️ 코스피 조회 실패: {e}")
            kospi_change, market_trend = 0.0, "정체"

        # --- VKOSPI (KRX Open API) ---
        vkospi = self._fetch_vkospi(end_date)



        # --------------------------------------------------------
        # 2. 감성 점수 계산 로직 (가중치 및 정규화 반영)
        # --------------------------------------------------------
        reasons = []

        # (1) V-KOSPI 정규화 (가중치 40%)
        # 기준: 30 이상 -> 0점 / 15 이하 -> 1점
        vk_val = vkospi['value']
        if vk_val >= 30:
            vk_score = 0.0
        elif vk_val <= 15:
            vk_score = 1.0
        else:
            # 15~30 사이 구간 선형 보간: (30 - 현재값) / 15
            vk_score = (30 - vk_val) / 15.0
        
        reasons.append(f"V-KOSPI {vk_val}: {'공포' if vk_val >= 25 else '안정' if vk_val <= 15 else '중립'}")

        # (2) 외국인 수급 정규화 (가중치 40%)
        # 기준: 강한 매도 -> 0점 / 강한 매수 -> 1점
        # ※ '강한'의 기준을 ±5,000억 원으로 가정 (MAX_FLOW = 5000)
        MAX_FLOW = 5000 
        if net_buy >= MAX_FLOW:
            fr_score = 1.0
        elif net_buy <= -MAX_FLOW:
            fr_score = 0.0
        else:
            # -5000 ~ +5000 구간을 0~1로 변환: (현재값 + 5000) / 10000
            fr_score = (net_buy + MAX_FLOW) / (MAX_FLOW * 2)
        
        reasons.append(f"외국인 수급: {foreign_trend} ({net_buy}억)")

        # (3) 코스피 변화율 정규화 (가중치 20%)
        # 기준: -3% 이하 -> 0점 / +3% 이상 -> 1점 (-0.03 ~ 0.03)
        if kospi_change >= 0.03:
            kp_score = 1.0
        elif kospi_change <= -0.03:
            kp_score = 0.0
        else:
            # -3% ~ +3% 구간을 0~1로 변환: (현재값 + 0.03) / 0.06
            kp_score = (kospi_change + 0.03) / 0.06
        
        reasons.append(f"코스피 모멘텀: {market_trend} ({(kospi_change*100):.2f}%)")

        # --- 최종 점수 산출 (가중합) ---
        final_score = (vk_score * 0.4) + (fr_score * 0.4) + (kp_score * 0.2)
        score = max(0.0, min(1.0, round(final_score, 2))) # 0~1 사이로 제한 및 소수점 2자리

        # --- 최종 라벨 결정 ---
        if score >= 0.8:
            label = "과열"
        elif score >= 0.6:
            label = "낙관"
        elif score >= 0.3: 
            label = "중립"
        else:
            label = "공포"

        # --------------------------------------------------------
        # 3. 최종 JSON 구조화
        # --------------------------------------------------------
        report = {
            "metadata": {
                "source": "Market_Agent",
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "target_date": end_date, # 분석 기준이 된 날짜 (ex: 20260414)
                "version": "1.0"
            },
            "analysis": {
                "sentiment_label": label,
                "sentiment_score": score,
                "confidence": 0.85, 
                "risk_signal": {
                    "fomo": score >= 0.8,
                    "panic": score <= 0.3
                }
            },
            "raw_data": {
                "vkospi": {
                    "value": vkospi['value'],
                    "change_weekly": vkospi['change']
                },
                "foreign_flow": {
                    "net_buy": net_buy,
                    "trend": foreign_trend
                },
                "market_momentum": {
                    "kospi_change": round(kospi_change, 4),
                    "trend": market_trend
                }
            },
            "reason": reasons
        }
        return report
