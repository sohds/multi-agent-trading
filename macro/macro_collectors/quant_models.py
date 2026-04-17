import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import statsmodels.api as sm
import warnings
from utils.logger import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("quant_models")

# [근본 해결] 롤링 윈도우 크기 설정 (5년: 약 1260 거래일)
# 너무 짧으면 노이즈에 취약하고, 너무 길면 과거의 구조적 변화가 현재에 과한 영향을 미침
TRAIN_WINDOW = 252 * 5 

def run_macro_quant_pipeline(df_merged: pd.DataFrame) -> dict:
    logger.info("  ▸ [Quant] 데이터 전처리 및 롤링 윈도우 슬라이싱...")
    df = df_merged.copy()
    
    # 1. 전처리 및 팩터 생성
    df['KOSPI_Ret'] = df['KOSPI'].pct_change() * 100
    df['USD_KRW_Ret'] = df['USD_KRW'].pct_change() * 100
    df['Term_Spread'] = df['Bond_10Y'] - df['Bond_3Y']
    df['Credit_Spread'] = df['Corp_3Y'] - df['Bond_3Y']
    df['Bank_Bond_Spread'] = df['Bank_Bond_1Y'] - df['Bond_1Y'] 
    df['CP_Spread'] = df['CP_91D'] - df['CD_91D']
    
    features_to_diff = ['Term_Spread', 'Credit_Spread', 'Bank_Bond_Spread', 'CP_Spread']
    for f in features_to_diff:
        df[f + '_Diff'] = df[f].diff()
        
    df.dropna(inplace=True)

    # ---------------------------------------------------------
    # [근본 해결: 미래 참조 편향 방지]
    # 모델 학습(fit)에는 오직 '오늘(T)' 이전의 TRAIN_WINDOW 기간만 사용합니다.
    if len(df) > TRAIN_WINDOW:
        df_train = df.tail(TRAIN_WINDOW)
    else:
        df_train = df
    # ---------------------------------------------------------
    
    # 2. PCA 요인 추출 (df_train 기준 학습)
    logger.info(f"  ▸ [Quant] PCA 학습 (최근 {len(df_train)}일 윈도우 사용)...")
    # [수정완료] Level(4개) + Diff(4개) + 주가/환율(2개) = 총 10개 피처 완벽 반영
    features = [
        'KOSPI_Ret', 'USD_KRW_Ret', 
        'Term_Spread', 'Credit_Spread', 'Bank_Bond_Spread', 'CP_Spread',
        'Term_Spread_Diff', 'Credit_Spread_Diff', 'Bank_Bond_Spread_Diff', 'CP_Spread_Diff'
    ]
    
    scaler = StandardScaler()
    # 미래 데이터를 배제하고 오직 윈도우 구간의 평균/표준편차로만 표준화 학습
    X_train_scaled = scaler.fit_transform(df_train[features])
    
    pca = PCA(n_components=1)
    pca.fit(X_train_scaled)
    pca_weights = pca.components_[0]

    # [수정완료] 10개 피처에 맞춘 기대 부호 배열 (Term Spread는 역방향(-1), 나머지는 정방향(1) 가정)
    expected_signs = np.array([-1, 1, -1, 1, 1, 1, -1, 1, 1, 1])
    # 다수결 합의: 가중치 합이 아닌 부호 일치 개수로 판단 (고가중 단일 팩터 지배 방지)
    alignment_score = (np.sum(np.sign(pca_weights) == expected_signs) -
                       np.sum(np.sign(pca_weights) != expected_signs))

    if alignment_score < 0:
        pca_weights = -pca_weights
        
    # 전체 데이터(df)에 대한 FSI 산출 (학습된 가중치로 transform만 수행)
    X_all_scaled = scaler.transform(df[features])
    df['FSI_Factor'] = np.dot(X_all_scaled, pca_weights)

    # 당일 핵심 동인 추출 (방향성 일치 필터링)
    fsi_diff = df['FSI_Factor'].iloc[-1] - df['FSI_Factor'].iloc[-2]
    delta_scaled_data = X_all_scaled[-1] - X_all_scaled[-2] 
    contrib_to_change = pca_weights * delta_scaled_data 
    
    masked_contrib = np.copy(contrib_to_change)
    if fsi_diff > 0:
        masked_contrib[masked_contrib <= 0] = -np.inf
        # 방향 일치 기여자가 없을 경우 전체 기여 중 최대값으로 폴백 (index 0 고정 방지)
        max_contrib_idx = int(np.argmax(masked_contrib) if not np.all(np.isinf(masked_contrib))
                              else np.argmax(contrib_to_change))
    else:
        masked_contrib[masked_contrib >= 0] = np.inf
        max_contrib_idx = int(np.argmin(masked_contrib) if not np.all(np.isinf(masked_contrib))
                              else np.argmin(contrib_to_change))
        
    top_feature_raw = features[max_contrib_idx]
    
    # 메타데이터 기반 동적 라벨링 (Level과 Diff 모두 완벽 대응)
    feature_meta = {
        'KOSPI_Ret': ('KOSPI 지수 상승', 'KOSPI 지수 하락'),
        'USD_KRW_Ret': ('원/달러 환율 상승', '원/달러 환율 하락'),
        
        # 1. 속도/가속도 (Diff) 피처
        'Term_Spread_Diff': ('장단기 금리차 확대 가속', '장단기 금리차 축소'),
        'Credit_Spread_Diff': ('신용 스프레드 확대 가속', '신용 스프레드 축소'),
        'Bank_Bond_Spread_Diff': ('은행채 스프레드 확대 가속', '은행채 스프레드 축소'),
        'CP_Spread_Diff': ('CP 스프레드 확대 가속', 'CP 스프레드 축소'),
        
        # 2. 절대 수준 (Level) 피처 - 새로 추가된 부분!
        'Term_Spread': ('장단기 금리차 절대수준 확대', '장단기 금리차 절대수준 완화'),
        'Credit_Spread': ('신용 스프레드 절대수준 확대', '신용 스프레드 절대수준 완화'),
        'Bank_Bond_Spread': ('은행채 스프레드 절대수준 확대', '은행채 스프레드 절대수준 완화'),
        'CP_Spread': ('CP 스프레드 절대수준 확대', 'CP 스프레드 절대수준 완화')
    }
    # delta_scaled_data의 부호 사용: contrib 계산과 동일한 기준이므로 Diff 피처의 2차 미분 불일치 해소
    text_index = 0 if delta_scaled_data[max_contrib_idx] > 0 else 1
    top_driver_text = feature_meta.get(top_feature_raw, (top_feature_raw, top_feature_raw))[text_index]
    
    # 3. 마코프 국면전환 모형 학습 (df_train 기간 기준)
    logger.info("  ▸ [Quant] 3-State 마코프 국면전환 모형 학습 중...")
    # [수정] 전체 df에 저장된 FSI_Factor 중, df_train의 기간(Index)에 해당하는 값만 안전하게 잘라서 사용합니다.
    model = sm.tsa.MarkovRegression(df['FSI_Factor'].loc[df_train.index], k_regimes=3, trend='c', switching_variance=True)
    result = model.fit(search_reps=50, disp=False)

    def _check_converged(r):
        return not (hasattr(r, 'mle_retvals') and
                    isinstance(r.mle_retvals, dict) and
                    not r.mle_retvals.get('converged', True))

    markov_converged = _check_converged(result)
    if not markov_converged:
        # 1차 실패 시 탐색 횟수를 4배로 늘려 재시도
        logger.warning("  ▸ [Quant] 경고: 1차 수렴 실패 (search_reps=50). search_reps=200으로 재시도...")
        result = model.fit(search_reps=200, disp=False)
        markov_converged = _check_converged(result)
        if markov_converged:
            logger.info("  ▸ [Quant] 재시도 후 수렴 성공.")
        else:
            logger.warning("  ▸ [Quant] 경고: 재시도 후에도 수렴 실패. 확률 추정치가 불안정할 수 있습니다.")

    # [근본 해결: 라벨 스위칭 방지 사후 정렬]
    state_means = {i: result.params[f'const[{i}]'] for i in range(3)}
    sorted_states = sorted(state_means, key=state_means.get)
    
    state_normal, state_caution, state_crisis = sorted_states

    # 오늘 시점의 확률만 추출 (Look-ahead bias 방지를 위해 전체 시계열 학습이 아닌 윈도우 학습 결과 사용)
    # filtered: 시점 t까지의 정보만 조건부 사용 → 룩어헤드 바이어스 방지
    # smoothed는 미래 정보를 역방향 사용하므로 나우캐스팅에 부적합
    latest_probs = result.filtered_marginal_probabilities.iloc[-1]
    
    # 가상의 결과 컬럼 생성 (보고서용)
    df['Prob_Normal'] = 0.0
    df['Prob_Caution'] = 0.0
    df['Prob_Crisis'] = 0.0
    df.loc[df.index[-1], 'Prob_Normal'] = latest_probs[state_normal]
    df.loc[df.index[-1], 'Prob_Caution'] = latest_probs[state_caution]
    df.loc[df.index[-1], 'Prob_Crisis'] = latest_probs[state_crisis]
    
    return generate_macro_report(df, top_driver_text, markov_converged)

# (generate_macro_report 함수는 이전과 동일한 SSOT 로직 유지)

def generate_macro_report(df_final: pd.DataFrame, top_driver_text: str, markov_converged: bool = True) -> dict:
    latest = df_final.iloc[-1]
    prev_week = df_final.iloc[-6] if len(df_final) >= 6 else df_final.iloc[-2]
    
    c_prob_normal = latest['Prob_Normal']
    c_prob_caution = latest['Prob_Caution']
    c_prob_crisis = latest['Prob_Crisis']
    
    dominant_prob = max(c_prob_normal, c_prob_caution, c_prob_crisis)

    # argmax 기반 분류: 어떤 국면도 50%를 넘지 않는 전환기에도 올바른 국면 레이블 부여
    # (0.5 임계값 사용 시 Normal 확률 35%에도 "정상/저위험"으로 오분류되는 버그 수정)
    regime_map = {
        0: ("정상/안정 (Normal)", "Low"),
        1: ("경계/둔화 (Caution)", "Medium"),
        2: ("위기/위험 (Crisis)", "High"),
    }
    dominant_state = int(np.argmax([c_prob_normal, c_prob_caution, c_prob_crisis]))
    regime, risk = regime_map[dominant_state]

    current_fsi = latest['FSI_Factor']
    prev_fsi = df_final.iloc[-2]['FSI_Factor']
    fsi_change = current_fsi - prev_fsi

    # KOSPI_Ret 기대 부호는 -1: KOSPI 상승 → FSI 하락이 정상적 공동 움직임
    # 두 값이 같은 부호(곱이 양수)면 주식-신용 시그널 분기(Divergence) 상황
    kospi_ret = latest['KOSPI_Ret']
    equity_fsi_diverging = (kospi_ret * fsi_change > 0)

    if fsi_change > 0:
        if equity_fsi_diverging:
            momentum_text = (
                f"위험 가속 — 채권·신용 시장 주도 "
                f"(FSI {fsi_change:+.3f}p 상승 / KOSPI {kospi_ret:+.2f}%와 방향 분기)"
            )
        else:
            momentum_text = f"위험 가속 (전일 대비 금융스트레스 지수 {fsi_change:+.3f}p 상승)"
        driver_action = "스트레스 상승을 주도(악화)하는 핵심 리스크 요인"
    else:
        if equity_fsi_diverging:
            momentum_text = (
                f"위험 둔화 — 채권·신용 시장 주도 "
                f"(FSI {fsi_change:+.3f}p 하락 / KOSPI {kospi_ret:+.2f}%와 방향 분기)"
            )
        else:
            momentum_text = f"위험 둔화 (전일 대비 금융스트레스 지수 {fsi_change:+.3f}p 하락)"
        driver_action = "스트레스 하락을 이끌며 시장을 안정화시키는 1위 기여 요인"

    xai_pca = (
        f"1. [PCA 당일 동인]: 전체 금융스트레스 지수(FSI)는 전일 대비 {fsi_change:+.3f}p 변동함. "
        f"'{top_driver_text}'(이)가 당일(전일 대비 일중 기준) {driver_action}으로 추출됨. "
        f"(※ 동인 방향은 일중 변화 기준이므로, 원시 지표의 주간 변동률과 방향이 상이할 수 있음)"
    )
    
    if "위기" in regime or "Crisis" in regime:
        xai_markov = (
            f"2. [마코프 국면전환 논리]: 단순한 가격 등락을 넘어, 채권·신용·단기자금 시장에서 "
            f"정상 구간을 이탈한 군집화된 변동성(Clustered Volatility)이 감지됨. "
            f"이에 따라 시스템 리스크 발현 가능성을 매우 높게 평가하여 {round(dominant_prob*100, 1)}% 확률로 "
            f"'{regime}' 상태로 확정함."
        )
    elif "경계" in regime or "Caution" in regime:
        xai_markov = (
            f"2. [마코프 국면전환 논리]: 주요 거시 지표들의 변동성이 점진적으로 확대되는 패턴이 포착됨. "
            f"모형은 이를 잠재적 리스크 전이 단계로 해석하여 {round(dominant_prob*100, 1)}% 확률로 "
            f"'{regime}' 국면을 부여함."
        )
    else:
        xai_markov = (
            f"2. [마코프 국면전환 논리]: 마코프 모형 분석 결과, 시장의 구조적 변동성이 낮게 유지되고 있으며 "
            f"정상적인 경제 사이클의 범주 내에 있음. 이에 따라 {round(dominant_prob*100, 1)}%의 확률로 "
            f"'{regime}' 국면으로 진단됨."
        )

    if equity_fsi_diverging:
        divergence_note = (
            f"\n  3. [시그널 다이버전스 경고]: KOSPI({kospi_ret:+.2f}%, 안정 신호)와 "
            f"FSI({fsi_change:+.3f}p, 스트레스 신호)가 서로 반대 방향의 시장 해석을 가리키고 있음. "
            f"FSI는 채권·신용·단기자금 시장의 스트레스를 종합하므로, "
            f"주식 가격 신호만으로 전체 금융 위험을 판단하면 과소·과대평가 가능성이 있음."
        )
        xai_text = xai_pca + "\n  " + xai_markov + divergence_note
    else:
        xai_text = xai_pca + "\n  " + xai_markov
        
    return {
        "raw_indicators": {
            "stock_market": {
                "KOSPI": {"current": round(latest['KOSPI'], 2), "dod_change_pct": round(latest['KOSPI_Ret'], 2)}
            },
            "fx_market": {
                "USD_KRW": {"current": round(latest['USD_KRW'], 2), "dod_change_pct": round(latest['USD_KRW_Ret'], 2)}
            },
            "bond_market": {
                "Term_Spread": {"current": round(latest['Term_Spread'], 3), "wow_change_pt": round(latest['Term_Spread'] - prev_week['Term_Spread'], 3)},
                "Credit_Spread": {"current": round(latest['Credit_Spread'], 3), "wow_change_pt": round(latest['Credit_Spread'] - prev_week['Credit_Spread'], 3)},
                "CP_Spread": {"current": round(latest['CP_Spread'], 3), "wow_change_pt": round(latest['CP_Spread'] - prev_week['CP_Spread'], 3)}
            },
            "banking_sector": {
                "Bank_Bond_Spread": {"current": round(latest['Bank_Bond_Spread'], 3), "wow_change_pt": round(latest['Bank_Bond_Spread'] - prev_week['Bank_Bond_Spread'], 3)}
            }
        },
        "quantitative_models": {
            "fsi_factor_score": round(current_fsi, 4),
            "markov_converged": markov_converged,
            "regime_probabilities": {
                "state_0_normal": round(c_prob_normal, 4),
                "state_1_caution": round(c_prob_caution, 4),
                "state_2_crisis": round(c_prob_crisis, 4)
            }
        },
        "objective_analysis": {
            "current_regime_diagnosis": (
                f"현재 한국 경기 국면은 {regime} 상태이며, 해당 국면 진입 확률이 {round(dominant_prob*100, 1)}%로 지배적임. "
                f"마코프 모형과 PCA 역산 결과, '{top_driver_text}'(전일 대비 일중 기준) 요인이 당일 {driver_action}으로 판별됨."
                + (" 단, 주가·환율 신호와 채권·신용 신호가 분기 중이므로 해석 시 유의 요망." if equity_fsi_diverging else "")
            ),
            "risk_assessment": (
                f"투자 환경 위험도는 {risk} 수준. "
                f"당일 스트레스 변동의 핵심 동인인 '{top_driver_text}'(전일 대비 일중 기준)에 대한 모니터링이 필요함."
            ),
            "momentum": momentum_text,
            "xai_reasoning": xai_text
        }
    }