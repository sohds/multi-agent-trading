# sector/ — 섹터/종목 에이전트 모듈

멀티에이전트 투자 브리핑 시스템에서 **섹터 에이전트** 역할을 담당합니다.
종목 하나에 대해 5가지 데이터(수급·실적·목표주가·상대강도·밸류에이션)를 수집하고,
불/베어 에이전트에게 전달할 정형 페이로드를 생성합니다.

---

## 폴더 구조

```
sector/
├── sector_main.py              # 실행 진입점
├── sector_agents/
│   └── sector_agent.py         # 통합 오케스트레이터
├── sector_collectors/
│   ├── supply_demand.py        # 수급 분석
│   ├── earnings.py             # 실적 분석 (DART)
│   ├── naver_finance.py        # 목표주가·투자의견 (네이버 증권)
│   ├── relative_strength.py    # 섹터 상대강도
│   ├── valuation.py            # 밸류에이션 (PER·PBR)
│   └── consensus_test.py       # 크롤링 테스트용 스크립트
├── utils/
│   └── logger.py               # 공통 로거
├── patch_pykrx.py              # pykrx 호환성 패치
├── requirements.txt
└── .env.example
```

---

## 데이터 흐름

```
sector_main.py
    └─▶ run_sector_agent(ticker, ticker_name, sector_etf)
            ├── [1/4] supply_demand.py      → payload["supply_demand"]
            ├── [2/4] earnings.py           → payload["earnings"]
            ├── [3/4] naver_finance.py      → payload["naver_finance"]
            └── [4/4] relative_strength.py  → payload["relative_strength"]
                       valuation.py         → payload["valuation"]
                                                    ↓
                                        콘솔 출력 + JSON 저장 (output/)
```

---

## 파일별 역할 및 I/O

### `sector_main.py` — 실행 진입점

실행 방법:
```bash
python sector_main.py
```

분석 대상은 `.env` 또는 아래 기본값을 사용합니다.

| 환경변수 | 기본값 | 설명 |
|---|---|---|
| `TARGET_TICKER` | `005930` | 종목 코드 |
| `TARGET_NAME` | `삼성전자` | 종목명 |
| `SECTOR_ETF_TICKER` | `091160` | 섹터 ETF 코드 (KODEX 반도체) |
| `OUTPUT_DIR` | `output` | JSON 저장 경로 |
| `SAVE_JSON` | `true` | JSON 저장 여부 |

**역할:** `run_sector_agent()` 호출 → 결과를 섹션별로 콘솔 출력 → `output/sector_agent_{ticker}_{timestamp}.json` 저장

---

### `sector_agents/sector_agent.py` — 통합 오케스트레이터

**Input:**
```python
run_sector_agent(
    ticker: str,        # 종목 코드  (예: "005930")
    ticker_name: str,   # 종목명     (예: "삼성전자")
    sector_etf: str,    # 섹터 ETF   (예: "091160")
) -> dict
```

**Output (페이로드 구조):**
```python
{
    "meta": {
        "ticker": str,
        "ticker_name": str,
        "sector_etf": str,
        "as_of": "YYYY-MM-DD HH:MM",
    },
    "supply_demand":     dict | None,
    "earnings":          dict | None,
    "naver_finance":     dict | None,
    "relative_strength": dict | None,
    "valuation":         dict | None,
    "errors":            list[str],   # 수집 실패 항목 메시지
}
```

4개 수집 모듈을 순차 호출하며, 각 모듈이 예외를 던져도 나머지는 계속 실행됩니다.
완성된 페이로드는 불/베어 에이전트에 그대로 전달됩니다.

---

### `sector_collectors/supply_demand.py` — 수급 분석

**데이터 소스:** `pykrx`

**Input:** `get_supply_demand_analysis(ticker: str)`

**Output:**
```python
{
    "20d":  { "foreign": float, "institutional": float, "individual": float },  # 억원, 누적 순매수
    "60d":  { ... },
    "120d": { ... },
    "streak": {
        "foreign_consecutive_buy":  int,    # 최근 5거래일 중 외국인 매수일 수
        "foreign_consecutive_sell": int,    # 최근 5거래일 중 외국인 매도일 수
        "institutional_5d_net":     float,  # 기관 5일 누적 순매수 (억원)
        "institutional_5d_trend":   str,    # "매수우위" | "매도우위"
    },
    "trend_consistency": bool,   # 20d·60d 외국인 방향 일치 여부
    "intensity_change":  str,    # "매수 강도 심화" | "매도 강도 심화" | "강도 유지 또는 완화"
}
```

> 20d·60d 핵심 데이터 수집 실패 시 `{"error": "데이터 수집 실패"}` 반환

---

### `sector_collectors/earnings.py` — 실적 분석

**데이터 소스:** DART OpenAPI (`DART_API_KEY` 필수)

**Input:** `get_earnings_analysis(ticker: str)`

**Output:**
```python
{
    "corp_code":     str,           # DART 기업 고유 코드
    "latest_period": str,           # 가장 최근 유효 분기 키 (예: "2025_3Q")
    "quarters": {
        "2025_3Q": { "op_income": float, "revenue": float, "net_income": float },  # 억원
        "2025_2Q": { ... },
        "2025_1Q": { ... },
        "2024_ANN": { ... },
        "2024_3Q": { ... },
        "2024_2Q": { ... },
    },
    "yoy": { "op_income_chg": float, "revenue_chg": float, "net_income_chg": float },  # %
    "qoq": { "op_income_chg": float },  # %
    "trend_3q": str,    # "3분기 연속 개선" | "3분기 연속 악화" | "혼조" | "데이터 부족"
    "note": str,        # 주의사항 메시지
}
```

> `DART_API_KEY` 미설정 시 삼성전자 더미 데이터 반환 (구조 확인용)  
> 어닝 서프라이즈/쇼크 판단은 불/베어 에이전트에게 위임합니다.

---

### `sector_collectors/naver_finance.py` — 목표주가·투자의견

**데이터 소스:** 네이버 증권 HTML 크롤링 (별도 API 키 불필요)

**Input:** `get_naver_finance_data(ticker: str)`

**Output:**
```python
{
    "current_price_info": {
        "current_price": float,     # 현재가 (원)
        "change": float,            # 전일 대비 (원)
        "change_pct": float,        # 등락률 (%)
        "volume": float,            # 거래량
        "market_cap_100m": float,   # 시가총액 (억원)
    },
    "analyst_opinions": {
        "reports": [                # 최근 리포트 목록 (최대 20건)
            { "date": str, "firm": str, "opinion": str, "target_price": float, "title": str }
        ],
        "avg_target_price": { "all": float, "1m": float, "3m": float },
        "buy_ratio":        { "all": float, "1m": float, "3m": float },
        "target_price_trend": str,
        "report_count":     { "all": int, "1m": int, "3m": int },
    },
    "market_info": {
        "52w_high": float,
        "52w_low":  float,
        "52w_position_pct": float,  # 52주 범위 내 현재 위치 (%)
        "foreign_ownership_pct": float,
    },
    "as_of": "YYYY-MM-DD HH:MM",
}
```

> 크롤링 특성상 네이버 증권 HTML 구조 변경 시 파싱 실패 가능.  
> 요청 간 딜레이(`NAVER_REQUEST_DELAY`)와 재시도(`NAVER_MAX_RETRIES`)는 `.env`로 조정합니다.

---

### `sector_collectors/relative_strength.py` — 섹터 상대강도

**데이터 소스:** `pykrx`

**Input:** `get_relative_strength_analysis(ticker: str, sector_etf: str)`

**Output:**
```python
{
    "sector_etf": str,
    "rs_history": {
        "1m": {
            "stock_ret":    float,  # 종목 수익률 (%)
            "sector_ret":   float,  # 섹터 ETF 수익률 (%)
            "kospi_ret":    float,  # KOSPI 수익률 (%)
            "rs_vs_sector": float,  # 종목 - 섹터 (양수: 섹터 대비 강세)
            "rs_vs_kospi":  float,  # 종목 - KOSPI (양수: 시장 대비 강세)
        },
        "3m": { ... },
        "6m": { ... },
        "1y": { ... },
    },
    "rs_trend": str,        # "지속 개선" | "지속 약화" | "최근 반전 (약화→개선)" | "최근 반전 (개선→약화)" | "혼조"
    "sector_issue": str,    # "섹터 전체 약세" | "종목 고유 약세" | "종목 상대 강세" | "섹터·종목 모두 KOSPI 상회"
    "strongest_period": str,  # 상대강도 최고 구간 ("1m" | "3m" | "6m" | "1y")
}
```

---

### `sector_collectors/valuation.py` — 밸류에이션

**데이터 소스:** `pykrx` (3년 펀더멘털 이력)

**Input:** `get_valuation_analysis(ticker: str)`

**Output:**
```python
{
    "current": {
        "base_date": str,   # 데이터 기준일 (장 휴일 시 최근 영업일로 자동 소급)
        "per": float,
        "pbr": float,
        "eps": float,
        "bps": float,
        "div_yield": float,
    },
    "per_band": {
        "current": float, "min_3y": float, "max_3y": float,
        "median_3y": float, "pct_3y": float,  # 3년 내 백분위 (%)
    },
    "pbr_band": { ... },    # 동일 구조
    "per_label": str,       # "역사적 저평가 구간 (하위 20%)" | "역사적 중간 구간" | "역사적 고평가 구간 (상위 20%)"
    "pbr_label": str,
    "eps_trend":   str,     # "EPS 개선 (YoY)" | "EPS 악화 (YoY)" | "데이터 부족"
    "eps_yoy_chg": float,   # EPS YoY 변화율 (%)
    "note": str,            # 저평가+EPS악화 등 주의 메시지
}
```

> 최대 7일 소급하여 유효한 펀더멘털 데이터를 탐색합니다.  
> 7일 내 데이터 없으면 `{"error": "최근 유효 데이터 없음"}` 반환.

---

### `utils/logger.py` — 공통 로거

**Input:** `get_logger(name: str) -> logging.Logger`

`LOG_LEVEL` 환경변수로 로그 레벨을 조정합니다 (기본: `INFO`).
포맷: `[YYYY-MM-DD HH:MM:SS] LEVEL | name | message`

---

## 환경 설정

`.env.example`을 복사하여 `.env`를 생성합니다.

```bash
cp .env.example .env
```

| 환경변수 | 필수 여부 | 설명 |
|---|---|---|
| `DART_API_KEY` | 필수 | [DART OpenAPI](https://opendart.fss.or.kr) 발급 (없으면 더미 데이터) |
| `TARGET_TICKER` | 선택 | 분석 종목 코드 (기본: `005930`) |
| `TARGET_NAME` | 선택 | 분석 종목명 (기본: `삼성전자`) |
| `SECTOR_ETF_TICKER` | 선택 | 섹터 ETF 코드 (기본: `091160`) |
| `NAVER_REQUEST_DELAY` | 선택 | 네이버 크롤링 딜레이 초 (기본: `1.0`) |
| `LOG_LEVEL` | 선택 | 로그 레벨 (기본: `INFO`) |
| `SAVE_JSON` | 선택 | JSON 저장 여부 (기본: `true`) |

---

## 설치 및 실행

```bash
pip install -r requirements.txt
python sector_main.py
```

---

## 현재 개발 상태

| 모듈 | 상태 | 비고 |
|---|---|---|
| `supply_demand.py` | 완성 | pykrx 기반 |
| `earnings.py` | 완성 | DART API 키 필요 / 없으면 더미 데이터 |
| `naver_finance.py` | 구현 중 | HTML 구조 변경 시 파싱 재검토 필요 |
| `relative_strength.py` | 완성 | pykrx 기반 |
| `valuation.py` | 완성 | pykrx 기반, 장 휴일 자동 소급 |
| LLM 분석 (불/베어) | 미구현 | 페이로드 수집까지만 완료, 판단은 외부 에이전트에 위임 |
