# 백테스팅 실험 계획서 — Bull-Bear 에이전트

**작성일**: 2026-05-05  
**작성자**: 서연 (Claude Code 보조)  
**상태**: 계획 단계 (팀 검토 후 구현 착수)

---

## 1. 목표

Bull-Bear 에이전트가 출력하는 **stance(매수/매도)**와 **confidence(확신도)**가 실제 주가 방향과 얼마나 일치하는지 과거 데이터로 검증한다.

현재 실험(exp_0~exp_2)은 "오늘 데이터를 넣었을 때 에이전트가 그럴듯한 논거를 내놓는가"를 확인했다. 백테스팅은 한 단계 더 나아가 **"그 판단이 실제로 맞는가"**를 묻는다.

### 핵심 질문

| # | 질문 | 검증 방법 |
|---|------|-----------|
| Q1 | Bull confidence > Bear confidence일 때 실제로 주가가 올랐는가? | 예측 방향 vs. N일 후 실제 등락 |
| Q2 | Confidence 값이 높을수록 예측 정확도가 높은가? | 분위별 적중률 비교 |
| Q3 | 2라운드 토론이 1라운드보다 더 정확한가? | ROUNDS=1 vs. ROUNDS=2 동일 날짜 비교 |
| Q4 | Macro/Sector 데이터가 추가되면 정확도가 오르는가? | 각 데이터 소스 ON/OFF 비교 |

---

## 2. 백테스팅이란 (비전공자 설명)

```
과거 날짜 D에서 에이전트가 어떤 판단을 내렸을지 재현
            ↓
그 날짜 기준으로 N일 뒤 실제 주가 확인
            ↓
판단이 맞았으면 ✅, 틀렸으면 ❌
            ↓
전체 테스트 케이스에서 적중률(%) 계산
```

예: 2024-01-15를 기준 날짜로 설정 → 에이전트가 "Bull 우세"라고 판정 →  
실제로 2024-01-29(+10거래일)에 주가가 올랐으면 적중.

---

## 3. 구현 필요 사항 (현재 코드와의 차이)

현재 코드는 **항상 오늘 날짜**를 기준으로 동작한다.  
백테스팅을 위해 다음 수정이 필요하다.

### 3-1. `collectors/technical_indicators.py` — 날짜 파라미터 추가

```python
# 현재 (오늘 기준으로만 동작)
def _get_ohlcv(ticker: str, days: int = 300) -> Optional[pd.DataFrame]:
    today = datetime.today().strftime("%Y%m%d")
    ...

# 변경 필요 (기준 날짜 주입 가능하도록)
def _get_ohlcv(ticker: str, days: int = 300, as_of: str | None = None) -> Optional[pd.DataFrame]:
    end = as_of or datetime.today().strftime("%Y%m%d")
    start = (datetime.strptime(end, "%Y%m%d") - timedelta(days=days)).strftime("%Y%m%d")
    ...

def get_technical_indicators(ticker: str, ticker_name: str, as_of: str | None = None) -> dict:
    df = _get_ohlcv(ticker, days=300, as_of=as_of)
    ...
    # date 필드도 as_of 기준으로 반환
```

> ✅ pykrx는 과거 날짜 OHLCV를 그대로 지원하므로 수정 범위가 가장 작다.

### 3-2. `package_builder.py` — as_of 파라미터 전파

```python
def build_input_package(
    ticker: str,
    ticker_name: str,
    as_of: str | None = None,          # 추가
    sector_payload: dict | None = None,
    macro_payload: dict | None = None,
    sentiment_payload: dict | None = None,
    topic_type: str = "종목",
) -> dict:
    technical = get_technical_indicators(ticker, ticker_name, as_of=as_of)  # as_of 전달
    ...
```

### 3-3. 새 스크립트 `bull-bear/backtest/backtest_runner.py`

백테스팅 전용 진입점. 아래 단계를 루프로 실행한다:

```
for each (ticker, date) in test_cases:
    1. 기준 날짜 D의 technical 지표 계산  (as_of=D, mask_for_backtest=True)
    2. 에이전트 실행 → bull_result, bear_result 획득
    3. 정답 계산: D+N거래일의 실제 종가 조회 (pykrx)
    4. 예측 방향 분류 (아래 규칙 적용)
    5. 결과 기록: {date, ticker, prediction, actual_direction, bull_conf, bear_conf, conf_diff}
```

**예측 방향 분류 규칙**:
```
conf_diff = bull.confidence - bear.confidence

if   conf_diff >  +0.05  →  prediction = "bullish"
elif conf_diff <  -0.05  →  prediction = "bearish"
else                     →  prediction = "neutral"  (확신 부족, 적중률 계산에서 제외)
```

> 임계값 0.05 근거: confidence 0.50 vs 0.51 같은 미미한 차이를 명확한 매수/매도 시그널로 보면 안 됨. 팀 합의 후 조정 가능.

### 3-4. 결과 분석 스크립트 `bull-bear/backtest/backtest_analysis.py`

결과 JSON을 읽어 통계 출력:
- 전체 방향 적중률
- Confidence 분위별 적중률
- ROUNDS=1 vs ROUNDS=2 비교

---

## 4. 데이터 누수 방지 — 마스킹 전략

### 왜 필요한가?

`gpt-5.4-mini`의 학습 데이터 cutoff은 **2025년 8월**이다. 우리가 백테스팅하려는 기간(2024-01 ~ 2025-12)의 대부분이 학습 데이터 범위 안에 있다.

LLM에게 "삼성전자 2024-06-15 기준 어떻게 보세요?"라고 물으면, LLM은 **2024년 7월 이후 실제 주가 흐름을 학습 데이터에서 이미 봤을 가능성이 높다.** 이 상태로 백테스트하면 에이전트가 "예측"하는 게 아니라 "기억"하는 셈이라 결과를 신뢰할 수 없다.

### 해결 — 입력 패키지 마스킹

LLM이 종목과 시점을 식별할 수 없도록 입력 데이터를 익명화한다.

| 필드 | 원본 | 마스킹 후 |
|------|------|-----------|
| `topic` | "삼성전자(005930) 지금 매수해도 되나?" | "종목 A 지금 매수해도 되나?" |
| `technical.ticker` | "005930" | "STOCK_A" |
| `technical.name` | "삼성전자" | "종목 A" |
| `technical.date` | "2024-06-15" | "T+0" 또는 제거 |
| `technical.price` (절대값) | 67,000원 | MA200 대비 비율로 정규화 (예: 1.18) |
| `technical.ma_5/20/60/...` | 절대 가격 | MA200 대비 비율 |
| `technical.support/resistance_level` | 절대 가격 | MA200 대비 비율 |

> RSI, MACD, 골든크로스 등 **상대적·패턴 기반 지표는 그대로 유지** — 종목 식별에 도움 안 됨.

### 마스킹 구현 위치

`package_builder.py`에 `mask_for_backtest=True` 옵션 추가:

```python
def build_input_package(
    ticker: str,
    ticker_name: str,
    as_of: str | None = None,
    mask_for_backtest: bool = False,    # 추가
    ...
):
    technical = get_technical_indicators(ticker, ticker_name, as_of=as_of)
    if mask_for_backtest:
        technical = _mask_technical(technical)
        ticker_name = "종목 A"
    ...
```

### 마스킹 한계 (정직하게 인정)

완벽한 마스킹은 불가능하다.
- **개별 가격 패턴**으로도 추정 가능성 있음 → 다종목 결과로 통계적 의미 확보
- **Macro/Sector 데이터**에 포함된 KOSPI 절대값, 환율, 금리 등은 시점을 거의 정확히 식별 가능 → 마스킹 어려움

### Macro/Sector 데이터 다루는 두 가지 접근

이번 백테스트는 다음 **두 트랙을 병행 실행**하여 결과 신뢰도를 차별화한다:

| 트랙 | 데이터 구성 | 마스킹 | 결과 해석 |
|------|------------|--------|-----------|
| **트랙 A — Clean** | Technical만 사용 | ON (정규화) | **절대 적중률 신뢰 가능** — baseline 측정용 |
| **트랙 C — Full** | Technical + Macro + Sector | OFF (식별 불가능) | **절대값 신뢰 불가**, 트랙 A 대비 **상대적 차이만** 의미 있음 ("데이터 추가 효과") |

**판단 기준**:
- 트랙 A 적중률 = 시스템의 깨끗한 baseline
- 트랙 C 적중률 - 트랙 A 적중률 = "Macro/Sector 데이터 추가의 순수 효과"
- 트랙 C 절대값 그 자체는 LLM 데이터 누수가 섞여 있음을 결과 보고서에 명시

> 두 트랙 모두 **동일한 케이스**(같은 종목·날짜·N)로 실행하여 차이 비교 가능하도록 한다.

### 마스킹 검증 절차 (선택)

트랙 A의 마스킹된 입력을 LLM에 던져 "이게 어느 종목/시점일 것 같나요?"라고 물어 식별 불가능 여부를 사전 검증.

---

## 5. 테스트 데이터셋 설계

### 5-1. 테스트 종목

섹터 편향 방지를 위해 **서로 다른 4개 섹터**의 대표 대형주를 선택한다.

| 섹터 | 종목 코드 | 종목명 | 선택 이유 |
|------|-----------|--------|-----------|
| 반도체/IT | 005930 | 삼성전자 | 유동성 최고, 지표 신뢰성 높음 |
| 자동차 | 005380 | 현대차 | 경기민감주 대표, KOSPI 변동성 다른 패턴 |
| 금융 | 105560 | KB금융 | 금리·매크로 영향 큰 섹터 |
| 바이오 | 207940 | 삼성바이오로직스 | 성장주 — 밸류에이션 중심 종목 |

> 초기엔 **삼성전자 1종목**으로 파이프라인 검증(Phase 1) 후 4종목 확대(Phase 2).

### 5-2. 테스트 기간

| 구분 | 날짜 범위 | 선택 이유 |
|------|-----------|-----------|
| **1차 (추천)** | 2024-01-01 ~ 2025-12-31 | 최근 2년, 상승·하락·횡보 국면 포함. N=20거래일 정답 확인을 위해 2025-12 이후 여유 확보 |
| 2차 (확장) | 2023-01-01 ~ 2023-12-31 | 데이터 범위 확장 시 추가 |

**샘플링 방법**: 매월 1일 (영업일 기준 nearest)

**단계별 케이스 수 및 비용**:

| 단계 | 종목 수 | 기간 | 케이스 수 | LLM 호출 | 추정 비용 (gpt-5.4-mini) |
|------|---------|------|-----------|----------|-------------------------|
| Phase 1 (파이프라인 검증) | 1 (삼성전자) | 24개월 | **24** | 48회 (Bull+Bear) | ~$0.5 |
| 전체 확장 (1라운드) | 4 | 24개월 | **96** | 192회 | ~$1~2 |
| Q3 검증 (ROUNDS=2 추가) | 4 | 24개월 | 96 추가 | 384회 (총합) | ~$3~5 |

### 5-3. 정답 정의 (Ground Truth)

```
예측 날짜: D
정답 확인 날짜: D + N 거래일

actual_direction = "bullish"  if  close[D+N] > close[D]
                 = "bearish"  if  close[D+N] < close[D]
                 = "neutral"  if  |변화율| < 1%  (노이즈 제거 임계값)
```

**검증 호라이즌 (N)**: 5일, 10일, 20일 세 가지 병렬 검증.

| N | 의미 | 적합한 사용 맥락 |
|---|------|------------------|
| 5거래일 (1주) | 단기 트레이딩 판단 | 기술적 지표 중심 |
| 10거래일 (2주) | 중단기 포지션 | Bull-Bear 기본 대상 |
| 20거래일 (1달) | 스윙 투자 | Macro·Sector 비중 높을 때 |

---

## 6. 사전 확인 — GT 라벨 분포 검증

에이전트 성능을 측정하기 **전에** 반드시 GT 라벨의 분포를 먼저 확인한다.

### 왜 필요한가?

GT 라벨은 "bullish / bearish / neutral" 세 가지뿐이다. 만약 테스트 기간이 전반적인 상승장이라면 GT에서 bullish 비율이 높아진다. 이 경우 에이전트가 항상 "bullish"를 출력해도 적중률이 높게 나올 수 있어, **에이전트의 실제 성능인지 시장 편향 덕분인지 구분이 안 된다.**

### 확인 방법

```
for each (ticker, date) in test_cases:
    GT 라벨 계산 (N=5, 10, 20 각각)

→ bullish / bearish / neutral 비율 출력
→ 이상적: bullish ≈ bearish ≈ 40~50%, neutral ≈ 10~20%
```

### 편향이 발견된 경우 대응

| 상황 | 대응 |
|------|------|
| bullish 비율 > 65% | 테스트 기간이 강세장 편향 → 2023년 데이터 추가하거나 하락 구간 종목 추가 |
| bearish 비율 > 65% | 약세장 편향 → 마찬가지로 기간 조정 |
| 편향 보정 불가 시 | **Balanced Accuracy** 사용 (클래스별 적중률 평균) |

```
Balanced Accuracy = (bullish 적중률 + bearish 적중률) / 2
```

단순 적중률과 Balanced Accuracy를 **항상 함께 보고**한다.

---

## 7. 평가 지표

### 7-1. 방향 적중률 (Directional Accuracy)

```
적중률 = 맞은 케이스 수 / 전체 유효 케이스 수
```

- "neutral" 케이스는 제외 후 계산
- **50% = 랜덤 수준** → 의미 있으려면 55%+ 목표

### 7-2. Confidence 구간별 적중률

neutral 예측(차이 < 0.05)은 제외 후, 나머지를 강도별로 분류:

```
Low   : 0.05 ≤ 차이 < 0.10  (약한 시그널)
Medium: 0.10 ≤ 차이 < 0.20  (중간 시그널)
High  :        차이 ≥ 0.20  (강한 시그널)
```

에이전트가 확신할수록 실제로 더 맞아야 "잘 교정된(calibrated)" 모델이라 할 수 있다.

### 7-3. 추가 지표

| 지표 | 설명 |
|------|------|
| Bull 편향률 | 전체 케이스 중 Bull 우세 판정 비율 (50%에서 크게 벗어나면 편향) |
| 평균 Confidence | Bull/Bear 각 평균 (일관성 체크) |
| 에러율 | JSON 파싱 실패 / API 오류 비율 |

---

## 8. 데이터 소스 별 백테스팅 가능 여부

| 데이터 소스 | 과거 데이터 가용성 | 복잡도 | 1차 포함 여부 |
|------------|-------------------|--------|--------------|
| **Technical** (pykrx) | ✅ 완전 지원 | 낮음 | **✅ 포함** |
| **Macro** (ECOS API) | ✅ 과거 지표 조회 가능 | 중간 (날짜별 API 호출) | ⚠️ 2차 |
| **Sector - 수급** (pykrx) | ✅ 날짜 지정 가능 | 중간 | ⚠️ 2차 |
| **Sector - 실적** (DART) | ✅ 분기별 공시 조회 | 높음 (공시 시점 매칭) | ⚠️ 2차 |
| **Sentiment - V-KOSPI** (yfinance) | ✅ 과거 데이터 지원 | 낮음 | ⚠️ 2차 |

> **1차 백테스팅 범위**: Technical 지표만 사용 (Macro/Sector/Sentiment=None)  
> 이를 통해 순수 기술적 분석만으로의 성능 기준선(baseline)을 확보한다.

---

## 9. 단계별 구현 계획

### Phase 0 — 사전 검증 (반나절)

```
[ ] gpt-5.4-mini의 temperature 파라미터 지원 여부 확인 (간단 호출 테스트)
[ ] pykrx 과거 OHLCV 조회 동작 확인 (as_of=2024-01-15 등 임의 날짜)
[ ] GT 라벨 분포 사전 산출 (4종목 × 24개월 × N=5/10/20)
[ ] 마스킹 검증 — 마스킹된 입력으로 LLM이 종목/시점 추정 못 하는지 확인
```

### Phase 1 — 기술적 지표 백테스팅 (2~3일)

```
[ ] technical_indicators.py: as_of 파라미터 추가
[ ] package_builder.py: as_of 및 mask_for_backtest 옵션 추가
[ ] backtest_runner.py: 루프 구현 (Macro/Sector/Sentiment=None, 마스킹 ON)
[ ] 삼성전자 2024-2025, 월간 샘플 24케이스 실행 (ROUNDS=1)
[ ] 결과 JSON 저장 및 기본 통계 출력 (적중률, Balanced Accuracy)
```

**예상 결과**: 기술적 지표만으로 방향 적중률 ~50~55%

### Phase 2 — 4종목 확장 + ROUNDS=2 비교 (3~4일)

```
[ ] 4종목 전체로 확장 실행 (96 케이스, ROUNDS=1)
[ ] 동일 96 케이스를 ROUNDS=2로 재실행 (Q3 검증용)
[ ] ROUNDS=1 vs ROUNDS=2 적중률 및 Confidence 비교
```

### Phase 3 — 트랙 C (Full) 실행: Macro + Sector 추가 (1주)

```
[ ] ECOS API 날짜별 과거 조회 구현
[ ] pykrx 수급 데이터 과거 날짜 조회 검증
[ ] V-KOSPI 과거 sentiment 계산 함수 작성
[ ] 동일 96 케이스에 Technical + Macro + Sector + Sentiment 추가 후 재실행 (트랙 C, 마스킹 OFF)
[ ] 트랙 A(Phase 2) vs 트랙 C 정확도 비교 (Q4 검증)
[ ] 트랙 C 절대 적중률은 LLM 데이터 누수 영향 명시
```

### Phase 4 — 분석 및 시각화 (2~3일)

```
[ ] backtest_analysis.py: Confidence 구간별 적중률 (Q2 검증)
[ ] 종목별·시기별·N별 분해 분석
[ ] 결과 마크다운 문서 작성 (팀 공유용)
```

---

## 10. 예상되는 한계 및 주의사항

### 10-1. 서바이벌 편향 (Survivorship Bias)
테스트 종목을 "현재 존재하는" 우량주로만 구성하면 과거 성과가 과도하게 좋게 나올 수 있다. 이번 실험은 학술적 검증보다 **시스템 동작 확인**이 목적이므로 1차에서는 허용하되, 결론 해석 시 주의.

### 10-2. LLM 비결정성 (Non-determinism)
동일한 입력에도 LLM 출력이 다를 수 있다. 같은 날짜를 3회 반복 실행하면 confidence가 달라질 수 있음 → 평균값 사용 또는 temperature=0 설정 검토.

> ⚠️ gpt-5.4-mini에서 `temperature` 파라미터 지원 여부 사전 확인 필요.

### 10-3. 룩-어헤드 바이어스 (Look-ahead Bias)
as_of 날짜 이후 데이터가 지표 계산에 포함되지 않도록 철저히 차단해야 한다.  
`pykrx.get_market_ohlcv(start, end, ticker)`의 `end` 파라미터가 as_of 날짜인지 **반드시 검증**.

### 10-4. API 비용
단계별 비용 추정은 §5-2 표 참조. 전체(Q1~Q4) 진행 시 누적 약 **$3~5**.  
실행 전 팀 예산 확인 권장.

### 10-5. DEBATE_ROUNDS=2 비용
Q3(라운드 비교) 검증 시 ROUNDS=2는 한 케이스당 4회 호출(Bull-Bear 2라운드)이라 ROUNDS=1 대비 2배 호출량.

---

## 11. 실험 결과 기대값 및 해석 가이드

| 결과 | 해석 | 권장 대응 |
|------|------|-----------|
| 적중률 < 50% | 에이전트 판단이 랜덤보다 나쁨 → 시스템 프롬프트 또는 데이터 문제 | 프롬프트 재검토, 데이터 파이프라인 점검 |
| 적중률 50~55% | 랜덤 수준 — 기술적 지표만으로의 한계 | Macro/Sector 추가 후 Phase 2로 진행 |
| 적중률 55~65% | **유의미한 예측력** — 실용 수준에 근접 | Confidence 보정 후 오케스트레이터 연동 |
| 적중률 > 65% | 예상 초과 성능 — 과적합 또는 데이터 누수 의심 | 룩-어헤드 바이어스 재확인 필수 |

---

## 12. 팀 논의 필요 사항

1. **API 비용 허용 범위** — Phase 1 실행 전 확인 ($1~3)
2. **정답 호라이즌 N** — 5/10/20일 중 팀의 투자 전략 시계(time horizon)에 맞는 N 선택
3. **Macro 과거 데이터 방식** — ECOS API 날짜별 호출 vs. 현재 상태 고정 사용
4. **결과 공유 형태** — 실험 결과를 팀 전체 공유 시 GitHub 커밋할 건지 (현재 experiments/ 는 gitignore)
