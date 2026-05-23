# multi-agent-trading

[BITAmin] 2026 1학기 프로젝트 — 멀티에이전트 교차 토론 기반 AI 주식 브리핑 시스템

---

## 프로젝트 개요

한국 주식시장을 대상으로 Bull(매수) 에이전트와 Bear(매도) 에이전트가 실시간 시장 데이터를 바탕으로 교차 토론하고, 그 결과를 Streamlit 대시보드로 제공하는 AI 투자 브리핑 시스템입니다.

**매매 실행이 아닌 콘텐츠 생성**이 목적이며, 에이전트의 논거·신뢰도·반박 근거를 모두 공개해 투자 교육 및 의사결정 보조에 초점을 맞춥니다.

---

## 시스템 아키텍처

```
외부 데이터 소스
├── pykrx               OHLCV, 수급 (외국인·기관·개인)
├── yfinance            KOSPI·KOSDAQ·S&P 500·달러원·금 등 주요 지수
├── 한국은행 ECOS API   장단기 금리차·신용 스프레드·CP 스프레드·은행채 스프레드
├── Naver Finance       종목 밸류에이션 (PER·PBR·EPS), 뉴스 헤드라인
└── VKOSPI              공포지수·심리 지표
        │
        ▼
┌─────────────────────────────────────┐
│          전문 데이터 에이전트         │
│  macro/     거시경제 지표 수집·FSI·  │
│             마코프 국면 전환 모형     │
│  sector/    밸류에이션·수급·         │
│             섹터 상대강도            │
│  market/    심리 지표·VKOSPI·        │
│             외국인 수급              │
└──────────────┬──────────────────────┘
               │  통합 입력 패키지
               ▼
┌─────────────────────────────────────┐
│        Bull / Bear 교차 토론         │
│  bull-bear/agents/bull_agent.py      │
│  bull-bear/agents/bear_agent.py      │
│  (OpenAI API, 2라운드 토론)          │
└──────────────┬──────────────────────┘
               │  stance · confidence · arguments · rebuttal
               ▼
┌─────────────────────────────────────┐
│       Streamlit 대시보드             │
│  dashboard/app.py       홈 (시장현황)│
│  pages/1_Debate.py      토론 페이지  │
│  pages/2_News_Translator.py 뉴스번역 │
│  pages/3_Quiz.py        투자 퀴즈    │
│  pages/4_News_Detail.py 뉴스 상세    │
└─────────────────────────────────────┘
```

---

## 폴더 구조

```
multi-agent-trading/
├── bull-bear/                   Bull/Bear 에이전트 + 기술적 지표
│   ├── agents/
│   │   ├── _base.py             LLM 호출 레이어 (OpenAI API, JSON 파싱, 후처리)
│   │   ├── bull_agent.py        Bull 에이전트 (낙관 프레임)
│   │   ├── bear_agent.py        Bear 에이전트 (비관 프레임)
│   │   └── field_glossary.json  필드명 → 한국어 해석 가이드 (LLM 주입용)
│   ├── collectors/
│   │   └── technical_indicators.py  pykrx + pandas_ta 기반 기술적 지표
│   ├── backtest/                백테스트 프레임워크 (다중 신호 ablation)
│   ├── experiments/             성능 검증 보고서 및 실험 결과 JSON
│   ├── package_builder.py       매크로·섹터·심리 데이터를 통합 입력 패키지로 조립
│   └── bull_bear_main.py        CLI 실행 진입점
│
├── macro/                       거시경제 에이전트
│   ├── macro_collectors/
│   │   ├── ecos_api.py          한국은행 ECOS API (금리·환율·스프레드)
│   │   └── quant_models.py      FSI (PCA 기반) + 마코프 국면 전환 모형
│   └── macro_agents/
│       └── macro_agent.py       거시 데이터를 구조화 JSON으로 변환
│
├── sector/                      섹터 에이전트
│   ├── sector_collectors/
│   │   ├── valuation.py         PER·PBR·EPS (Naver Finance 크롤링)
│   │   ├── supply_demand.py     외국인·기관·개인 수급 (pykrx)
│   │   ├── relative_strength.py 종목·섹터·KOSPI 상대강도
│   │   └── earnings.py          실적 데이터
│   └── sector_agents/
│       └── sector_agent.py      섹터 데이터 통합 분석
│
├── market/                      시장 심리 에이전트
│   ├── market_collectors/
│   │   └── sentiment_collector.py  VKOSPI·외국인 수급·시장 모멘텀
│   └── market_agents/
│       └── sentiment_agent.py   심리 점수·패닉·FOMO 신호 산출
│
├── debate/                      토론 주제 선정
│   ├── naver_headline_crawler.py  네이버 금융 헤드라인 수집
│   ├── debate_topic_agent.py    LLM 기반 토론 주제 생성
│   └── debate_runner.py         토론 오케스트레이션
│
├── news-translator/             금융 뉴스 번역기
│   ├── news_helper/             FastAPI 앱 + LLM 번역 로직
│   └── data/terms_800_preprocessed.json  금융 용어 800개 사전
│
├── news-quiz/                   투자 퀴즈 생성기
│   └── quiz_engine.py
│
├── dashboard/                   Streamlit 대시보드
│   ├── app.py                   홈 (시장 현황 + 뉴스 미리보기)
│   ├── pages/
│   │   ├── 1_Debate.py          Bull/Bear 토론 메인 페이지
│   │   ├── 2_News_Translator.py 뉴스 번역기
│   │   ├── 3_Quiz.py            투자 퀴즈
│   │   └── 4_News_Detail.py     뉴스 상세
│   └── utils/
│       └── styles.py            공통 CSS 인젝션
│
├── config/                      런타임 세션 상태 저장 (자동 생성)
│   ├── session.json             토론 결과 캐시
│   └── support_data.json        입력 패키지 캐시
│
└── requirements.txt
```

---

## 핵심 기능

### Bull / Bear 교차 토론

- 동일한 입력 패키지(기술적 지표·거시·섹터·심리)를 Bull·Bear 에이전트가 각자의 프레임으로 해석
- **2라운드** 구조: 1라운드에서 초기 논거 제시 → 2라운드에서 상대 주장을 직접 인용·반박
- `confidence` 값은 주관적 자신감이 아닌 **신호 강도** 기준으로 산출 (0.8+ = 3개 이상 신호 일치)
- LLM 출력 후처리(`_sanitize_output`)로 내부 필드명(`regime_probabilities`, `rsi_14` 등)을 자연어로 강제 치환

### 거시 모델

- **FSI (금융스트레스지수)**: KOSPI·환율·금리·스프레드 5개 지표의 PCA 합성 지수
- **마코프 국면 전환 모형**: 정상(state_0) / 주의(state_1) / 위기(state_2) 국면 확률 실시간 산출

### 섹터 분석

| 분류 | 지표 |
|------|------|
| 밸류에이션 | PER·PBR 3년 히스토리 백분위, EPS YoY 변화율 |
| 수급 | 외국인·기관 20일 누적 순매수, 연속 매수/매도 일수 |
| 상대강도 | 1개월·3개월·6개월·1년 종목 vs 섹터 vs KOSPI |

### 시장 심리

- VKOSPI 공포지수, 외국인 순매수 흐름, KOSPI 당일 등락률
- 심리 점수 0~1 (0=극단적 공포, 1=극단적 탐욕), 패닉·FOMO 신호 자동 감지

### 대시보드

- **홈**: yfinance 기반 주요 지수(KOSPI·KOSDAQ·S&P 500·나스닥·닛케이·달러원·금) SVG 스파크라인 + 5일 추이
- **토론 페이지**: 종목 코드 입력 → 실시간 Bull/Bear 토론 → 채팅·카드 2가지 UI 전환
- **뉴스 번역기**: 금융 전문용어 800개 매핑 기반 LLM 번역
- **투자 퀴즈**: 당일 뉴스 기반 OX 퀴즈 자동 생성

---

## 백테스트 결과 요약

`bull-bear/backtest/`에서 신호 조합(매크로·섹터·심리) ablation 실험을 수행했습니다.

| 실험 | 신호 조합 | 비고 |
|------|----------|------|
| phase3a | macro | 기저선 |
| phase3b | macro + sector | 섹터 수급·밸류에이션 추가 |
| phase3c | macro + sector + sentiment | 심리 지표 추가 |
| round2/3 | 전체 신호 반복 검증 | 안정성 확인 |

- 좋은 지표 종목(SK하이닉스): Bull confidence 0.91 > Bear confidence 0.86 ✓
- 나쁜 지표 종목(틱톡): Bear confidence 0.88 > Bull confidence 0.81 ✓
- 2라운드에서 rebuttal이 상대 주장의 구체적 수치를 명시적으로 인용하는 품질 개선 확인

자세한 결과는 [`bull-bear/experiments/FINAL_SUMMARY.md`](bull-bear/experiments/FINAL_SUMMARY.md) 참조.

---

## 환경 설정 및 실행

### 1. 의존성 설치

```bash
# Python 3.11 이상 권장
pip install -r requirements.txt
```

> **Python 3.13 주의**: `pykrx`가 내부적으로 `pkg_resources`를 사용합니다.
> `requirements.txt`에 `setuptools==69.5.1`이 고정되어 있으므로 별도 조치 불필요.

### 2. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다:

```dotenv
# 필수
OPENAI_API_KEY=sk-...

# 한국은행 ECOS API (거시 데이터)
ECOS_API_KEY=...

# 선택 (기본값 사용 가능)
TARGET_TICKER=005930       # 분석 종목 코드
TARGET_NAME=삼성전자         # 분석 종목명
SECTOR_ETF_TICKER=091160   # 섹터 ETF 코드
OPENAI_MODEL=gpt-4o        # LLM 모델
USE_MACRO=true
USE_SECTOR=true
USE_MARKET=true
```

### 3. 대시보드 실행

```bash
streamlit run dashboard/app.py
```

브라우저에서 `http://localhost:8501` 접속.

### 4. CLI로 Bull/Bear 토론만 실행

```bash
cd bull-bear
python bull_bear_main.py

# 환경변수로 종목·라운드 지정
TARGET_TICKER=000660 TARGET_NAME=SK하이닉스 python bull_bear_main.py
```

결과는 `bull-bear/output/debate_<종목코드>_<날짜시간>.json`으로 저장됩니다.

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.11+ |
| LLM | OpenAI API (`gpt-4o` / `gpt-4o-mini`) |
| 대시보드 | Streamlit |
| 주식 데이터 | pykrx, yfinance |
| 기술적 지표 | pandas_ta |
| 거시 모델 | scikit-learn (PCA), statsmodels (HMM) |
| 크롤링 | requests, BeautifulSoup4, Selenium |
| 뉴스 번역 백엔드 | FastAPI, uvicorn |

---

## 에이전트 인터페이스

Bull/Bear 에이전트 입출력 스펙 전체는 [`bull-bear/agent_interface_spec.md`](bull-bear/agent_interface_spec.md)에 정의되어 있습니다.

**입력 패키지 구조:**

```json
{
  "topic":    "분석 주제",
  "topic_type": "종목 | 시장전체 | 테마",
  "technical": { "price": ..., "rsi_14": ..., "macd_signal": ..., ... },
  "macro":     { "raw_indicators": ..., "quantitative_models": ..., ... },
  "sector":    { "valuation": ..., "supply_demand": ..., "relative_strength": ... },
  "sentiment": { "analysis": ..., "raw_data": ... },
  "news_events": { "news_available": false }
}
```

**에이전트 출력 구조:**

```json
{
  "stance":     "bullish | bearish",
  "confidence": 0.0,
  "arguments":  [{ "claim": "...", "data_ref": "technical.rsi_14" }],
  "rebuttal":   "상대 논거에 대한 토론 말투 반박 (null 가능)",
  "summary":    "한 줄 요약"
}
```

---

## 참고 논문

- **TradingAgents** (arXiv: 2412.20138, UCLA + MIT, 2024) — Bull/Bear 교차 토론 파이프라인의 학술적 선행 연구
- **TradingGPT** (Li et al., 2023) — 멀티에이전트 금융 분석 프레임워크
- **Heterogeneous LLM Agents for Financial Sentiment Analysis** (Xing, 2024)

---

## 주의사항

이 시스템은 **투자 판단 참고용 콘텐츠 생성 도구**입니다. 자동 매매·주문 실행 기능은 포함하지 않으며, 에이전트의 판단이 실제 수익을 보장하지 않습니다.
