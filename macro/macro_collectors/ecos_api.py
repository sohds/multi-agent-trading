import os
import pandas as pd
import requests
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger("ecos_api")

def fetch_ecos_data(api_key, stat_code, item_code, start_date, end_date, cycle_type="D"):
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    url = f"http://ecos.bok.or.kr/api/StatisticSearch/{api_key}/json/kr/1/10000/{stat_code}/{cycle_type}/{start_str}/{end_str}/{item_code}"
    
    response = requests.get(url)
    data = response.json()
    if 'StatisticSearch' not in data:
        logger.error(f"데이터 조회 실패 (코드: {stat_code} / {item_code}): {data}")
        return pd.DataFrame()
        
    rows = data['StatisticSearch']['row']
    df_ecos = pd.DataFrame(rows)
    df_ecos['TIME'] = pd.to_datetime(df_ecos['TIME'])
    df_ecos.set_index('TIME', inplace=True)
    df_ecos['DATA_VALUE'] = df_ecos['DATA_VALUE'].astype(float)
    return df_ecos[['DATA_VALUE']]

def get_macro_raw_data() -> pd.DataFrame:
    """
    김성아 외(2015) 논문 기반 4대 부문 핵심 거시 지표 수집 및 병합
    (주식: KOSPI, 외환: 환율, 채권: 장단기/신용/CP, 은행: 은행채)
    """
    ECOS_API_KEY = os.getenv("ECOS_API_KEY")
    if not ECOS_API_KEY or ECOS_API_KEY == "your_ecos_api_key_here":
        raise ValueError("ECOS_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

    end_dt = datetime.today()
    # [수정] 표본 크기 확장: 거시 사이클(코로나19, 금리인상기 등) 학습을 위해 10년(3650일)으로 기간 대폭 확대
    start_dt = end_dt - timedelta(days=365 * 10) 
    
    logger.info("  ▸ [ECOS] 4대 부문(주식/외환/채권/은행) 10년치 장기 데이터 호출 중...")
    
    df_kospi = fetch_ecos_data(ECOS_API_KEY, "802Y001", "0001000", start_dt, end_dt)
    df_kospi.columns = ['KOSPI']
    
    df_usd = fetch_ecos_data(ECOS_API_KEY, "731Y001", "0000001", start_dt, end_dt)
    df_usd.columns = ['USD_KRW']
    
    df_bond_3y = fetch_ecos_data(ECOS_API_KEY, "817Y002", "010200000", start_dt, end_dt)
    df_bond_3y.columns = ['Bond_3Y']
    
    df_bond_10y = fetch_ecos_data(ECOS_API_KEY, "817Y002", "010210000", start_dt, end_dt)
    df_bond_10y.columns = ['Bond_10Y']
    
    df_corp_3y = fetch_ecos_data(ECOS_API_KEY, "817Y002", "010300000", start_dt, end_dt)
    df_corp_3y.columns = ['Corp_3Y']
    
    # [수정] 국고채 1년물 (산금채 1년물과 스프레드 계산용)
    df_bond_1y = fetch_ecos_data(ECOS_API_KEY, "817Y002", "010190000", start_dt, end_dt)
    df_bond_1y.columns = ['Bond_1Y']
    
    # [수정] 산금채 1년물 (은행채 대용)
    df_bank_1y = fetch_ecos_data(ECOS_API_KEY, "817Y002", "010260000", start_dt, end_dt)
    df_bank_1y.columns = ['Bank_Bond_1Y']
    
    # [NEW] CD 91일물 (올바른 코드 적용)
    df_cd_91d = fetch_ecos_data(ECOS_API_KEY, "817Y002", "010502000", start_dt, end_dt)
    df_cd_91d.columns = ['CD_91D']
    
    # [NEW] CP 91일물 (올바른 코드 적용)
    df_cp_91d = fetch_ecos_data(ECOS_API_KEY, "817Y002", "010503000", start_dt, end_dt)
    df_cp_91d.columns = ['CP_91D']
    
    logger.info("  ▸ [ECOS] 전체 시장 데이터 병합 및 시점 동기화(Alignment) 중...")
    
    # 1. 데이터 병합 (Outer Join)
    df_merged = df_kospi.join(
        [df_usd, df_bond_3y, df_bond_10y, df_corp_3y, df_bond_1y, df_bank_1y, df_cd_91d, df_cp_91d], 
        how='outer'
    )
    
    # 2. [LCO 꼬리 자르기] 모든 지표가 결측치 없이 완벽하게 존재하는 가장 최근 날짜 찾기
    last_complete_date = df_merged.dropna().index.max()
    
    if pd.isna(last_complete_date):
        raise ValueError("완전한 데이터가 존재하는 날짜를 찾을 수 없습니다. API 상태나 기간을 확인하세요.")
        
    logger.info(f"  ▸ [ECOS] 동기화 기준일(LCO Date) 확정: {last_complete_date.strftime('%Y-%m-%d')}")
    
    # 3. 확정된 기준일까지만 데이터를 잘라내어 '불완전한 미래 데이터'의 억지 결합 방지
    df_aligned = df_merged.loc[:last_complete_date].copy()
    
    # 4. 잘라낸 후, 과거 구간 내에 있는 정상적인 휴장일(공휴일 등)의 빈칸만 안전하게 앞의 값으로 채움
    df_aligned.ffill(inplace=True)
    
    # 5. 맨 앞단(start_dt 부근)의 결측치 제거
    df_aligned.dropna(inplace=True)
    
    return df_aligned