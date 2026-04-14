# 📈 Market Agent

한국 주식시장의 **시장 심리(Market Sentiment)** 를 자동으로 수집·분석하여 JSON 리포트를 생성하는 에이전트입니다.  
멀티 에이전트 트레이딩 시스템(`multi-agent-trading`)의 하위 모듈로 동작합니다.

---

## 📁 디렉터리 구조

```
multi-agent-trading/
├── market/
│   ├── market_main.py                    # 메인 실행 파일
│   ├── market_collectors/
│   │   └── sentiment_collector.py        # 시장 심리 수집·분석 클래스
│   └── utils/
│       └── patch_pykrx.py               # pykrx KRX 로그인 패치 스크립트
└── output/
    └── market_agent_YYYYMMDD_HHMMSS.json # 분석 결과 저장 경로
```

---

## ⚙️ 주요 기능

### 1. 시장 심리 지표 수집

| 지표 | 출처 | 설명 |
|------|------|------|
| **VKOSPI** | KRX Open API | 코스피 200 변동성 지수 (공포·탐욕 측정) |
| **외국인 수급** | pykrx | KOSPI 외국인 순매수/순매도 금액 (억 원) |
| **코스피 모멘텀** | Yahoo Finance (`^KS11`) | 최근 7일 코스피 지수 변화율 |

### 2. sentiment score 산출 (0.0 ~ 1.0)

세 지표에 가중치를 부여한 후 선형 정규화로 합산합니다.

| 지표 | 가중치 | 정규화 기준 |
|------|--------|------------|
| VKOSPI | **40%** | 30 이상 → 0점 / 15 이하 → 1점 |
| 외국인 수급 | **40%** | ±5,000억 원 기준 선형 변환 |
| 코스피 모멘텀 | **20%** | ±3% 기준 선형 변환 |

### 3. 감성 라벨 분류

| 점수 범위 | 라벨 |
|-----------|------|
| 0.8 이상 | 과열 |
| 0.6 ~ 0.8 | 낙관 |
| 0.3 ~ 0.6 | 중립 |
| 0.3 미만 | 공포 |

---

## 🔧 설치 및 환경 설정

### 1. 의존 패키지 설치

```bash
pip install pykrx yfinance requests python-dotenv
```

### 2. 환경 변수 설정 (`.env`)

프로젝트 루트에 `.env` 파일을 생성하고 아래 변수를 설정합니다.

```env
# KRX Open API 인증키 (VKOSPI 조회용)
KRX_AUTH_KEY=your_krx_auth_key_here

# KRX 데이터 포털 로그인 (pykrx 세션 유지용)
KRX_ID=your_krx_id
KRX_PW=your_krx_password
```

> **KRX_ID / KRX_PW** : [KRX 데이터 포털](https://data.krx.co.kr)에서 회원가입을 진행한 후, 아이디와 비밀번호를 입력합니다.

> **KRX_AUTH_KEY** : [KRX 데이터 포털](https://data.krx.co.kr)에서 API 인증키 신청 후 발급받을 수 있습니다. 추가로 https://openapi.krx.co.kr/contents/OPP/USES/service/OPPUSES001_S2.cmd?BO_ID=rPBjbLtScMwmSXWDOYPd 에서 '파생상품지수 시세정보'의 API 이용신청을 해야합니다.

### 3. pykrx 패치 (최초 1회)

`market_main.py` 실행 시 자동으로 패치가 적용됩니다. 필요 시 수동으로도 실행 가능합니다.

```bash
python market/utils/patch_pykrx.py
```


---

## 🚀 실행 방법

```bash
cd multi-agent-trading/market
python market_main.py
```

실행 흐름:

1. `patch_pykrx.py` 자동 실행 → pykrx 환경 점검
2. `.env` 환경변수 로드
3. 시장 데이터 수집 (VKOSPI · 외국인 수급 · 코스피)
4. 감성 점수 산출 및 라벨 분류
5. 터미널에 결과 출력
6. `output/market_agent_YYYYMMDD_HHMMSS.json` 파일 저장

---

## 📄 출력 JSON 구조

```json
{
  "metadata": {
    "source": "Market_Agent",
    "generated_at": "2026-04-14 09:00:00",
    "target_date": "20260413",
    "version": "1.0"
  },
  "analysis": {
    "sentiment_label": "중립",
    "sentiment_score": 0.52,
    "confidence": 0.85,
    "risk_signal": {
      "fomo": false,
      "panic": false
    }
  },
  "raw_data": {
    "vkospi": {
      "value": 20.5,
      "change_weekly": -1.2
    },
    "foreign_flow": {
      "net_buy": 320,
      "trend": "순매수"
    },
    "market_momentum": {
      "kospi_change": 0.0124,
      "trend": "상승"
    }
  },
  "reason": [
    "V-KOSPI 20.5: 중립",
    "외국인 수급: 순매수 (320억)",
    "코스피 모멘텀: 상승 (1.24%)"
  ]
}
```

| 필드 | 설명 |
|------|------|
| `metadata` | 생성 시각, 분석 기준일 등 메타 정보 |
| `analysis.sentiment_label` | 최종 심리 라벨 (과열/낙관/중립/공포) |
| `analysis.sentiment_score` | 0.0 ~ 1.0 정규화 점수 |
| `analysis.risk_signal.fomo` | 점수 ≥ 0.8일 때 과열 경고 |
| `analysis.risk_signal.panic` | 점수 ≤ 0.3일 때 공포 경고 |
| `raw_data` | 수집된 원시 지표값 |
| `reason` | 점수 산출 근거 요약 |

---

## ⚠️ 유의 사항

- **VKOSPI** 는 전영업일 기준으로 조회됩니다. 주말·공휴일에는 데이터가 없어 기본값(20.0)이 사용됩니다.
- **외국인 수급** 은 pykrx를 통해 스크래핑되므로 KRX 서버 상태에 따라 간헐적으로 실패할 수 있습니다.
- 출력 파일은 `multi-agent-trading/output/` 디렉터리에 타임스탬프 형식으로 저장되며, 폴더가 없으면 자동 생성됩니다.

---

## 🗂️ 다른 에이전트와의 연동

Market Agent가 생성한 JSON 파일은 `output/` 폴더에 저장되어 다른 에이전트(예: 종목 분석 에이전트, 포트폴리오 에이전트)가 읽어 활용할 수 있습니다.

