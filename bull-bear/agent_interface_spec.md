# 에이전트 간 데이터 전달 인터페이스 스펙 (Phase 0)

> **목적**: 각 에이전트가 무엇을 출력하고, 불/베어 에이전트가 무엇을 입력받는지 확정.
> 구현 전 이 스펙을 고정하여, 에이전트 간 데이터 계약을 명확히 한다.
>
> **범위**: 매크로 → 불/베어, 섹터종목 → 불/베어, 시장심리 → 불/베어, 불/베어 → 오케스트레이터
>
> **설계 원칙**: 불/베어 에이전트는 동일한 패키지를 받는다. 해석 프레임(낙관 vs 비관)만 시스템 프롬프트로 분리한다.

---

## 1. 매크로 에이전트 출력 스펙

**역할**: 한국은행 ECOS 데이터를 수집하고, PCA 기반 금융스트레스지수(FSI)와 마코프 국면전환 모형으로 거시경제 국면을 정량 분석한다.

**데이터 소스**: 한국은행 ECOS API (`ECOS_API_KEY` 필수)

**수집 지표**: KOSPI, 원/달러 환율, 국고채 3년물·10년물(장단기금리차), 우량회사채 AA-(신용스프레드)

**분석 프레임**: PCA → 단일 FSI 점수 추출 → 3-State 마코프 국면전환 모형(정상/경계/위기) 확률 도출

### 출력 JSON

```json
{
  "meta": {
    "as_of": "2026-03-31 15:30",
    "base_models": [
      "3-State Markov Regime Switching",
      "PCA-based FSI"
    ]
  },
  "raw_indicators": {
    "market_index": {
      "KOSPI": {
        "current": 5277.3,
        "dod_change_pct": 0.0,
        "interpretation": "하락"
      },
      "USD_KRW": {
        "current": 1513.4,
        "dod_change_pct": 0.35
      }
    },
    "interest_rates_spread": {
      "Term_Spread": {
        "current": 0.327,
        "wow_change_pt": 0.015,
        "status": "정상"
      },
      "Credit_Spread": {
        "current": 0.614,
        "wow_change_pt": 0.016
      }
    }
  },
  "quantitative_models": {
    "fsi_factor_score": -0.6779,
    "regime_probabilities": {
      "state_0_normal": 0.7849,
      "state_1_caution": 0.1518,
      "state_2_crisis": 0.0633
    }
  },
  "objective_analysis": {
    "current_regime_diagnosis": "현재 한국 경기 국면은 정상/안정 (Normal) 상태이며, 해당 국면 진입 확률이 78.5%로 지배적임.",
    "risk_assessment": "투자 환경 위험도는 Low 수준. 장단기 금리차가 0.327%p를 기록하고 있음.",
    "momentum": "위축"
  },
  "errors": []
}
```

> **필드 설명**
> - `fsi_factor_score`: PCA로 압축한 금융스트레스지수. 음수일수록 시장 안정, 양수일수록 스트레스 심화.
> - `regime_probabilities`: 세 국면 확률의 합은 항상 1.0. `state_0_normal` 우세 = 정상 국면.
> - `momentum`: 전일 FSI 대비 방향 ("개선" / "위축").

### 전달 방식 결정 사항

| 항목 | 결정 | 근거 |
|---|---|---|
| 논거(ammunition) 포함 여부 | **미포함** — B안 채택 | 매크로 에이전트는 퀀트 데이터만 생성. 불/베어 에이전트가 원본 지표를 직접 해석해 논거 생성. 역할 분리 명확화. |
| `macro_score` (오케스트레이터용) | **`state_0_normal − state_2_crisis`** 로 산출 | -1.0 ~ +1.0 범위 보장. 위기 확률 높을수록 음수. |
| `meta`, `errors` | **제외** (불/베어 미전달) | 에이전트 내부 메타데이터. 논거 생성에 불필요. |

---

## 2. 섹터종목 에이전트 출력 스펙

**역할**: 종목의 수급·실적·섹터 흐름·밸류에이션을 수집하고 정량 데이터를 구조화한다.

**데이터 소스**: `pykrx` (수급, 섹터ETF, 밸류에이션), DART API (재무제표), 네이버/한경 크롤링 (목표주가)

### 출력 JSON

```json
{
  "supply_demand": {
    "20d":  { "foreign": -214481.8, "institutional": -24227.0, "individual": 238708.8 },
    "60d":  { "foreign": -333075.3, "institutional": -48120.5, "individual": 381195.8 },
    "120d": { "foreign": -262595.7, "institutional": -10300.2, "individual": 272895.9 },
    "streak": {
      "foreign_consecutive_buy":  0,
      "foreign_consecutive_sell": 5,
      "institutional_5d_net":     -24227.0,
      "institutional_5d_trend":   "매도우위"
    },
    "trend_consistency": true,
    "intensity_change":  "매도 강도 심화"
  },

  "earnings": {
    "corp_code":     "00126380",
    "latest_period": "2025_3Q",
    "quarters": {
      "2025_3Q": { "op_income": 121660.6, "revenue": 860617.5 },
      "2025_2Q": { "op_income":  46760.6, "revenue": 745663.2 },
      "2025_1Q": { "op_income":  66852.7, "revenue": 791405.0 },
      "2024_3Q": { "op_income":  91833.7, "revenue": 790987.3 }
    },
    "yoy": { "op_income_chg": 0.325, "revenue_chg": 0.088 },
    "qoq": { "op_income_chg": 1.602 },
    "trend_3q": "혼조",
    "note": ""
  },

  "naver_finance": {
    "current_price_info": {
      "current_price":   167200.0,
      "change":          -1800.0,
      "change_pct":      -1.06,
      "volume":          15234567.0,
      "market_cap_100m": 9978240.0
    },
    "analyst_opinion": {
      "avg_target_price":      { "1m": null, "3m": null },
      "target_price_gap_rate": null,
      "target_price_trend":    "N/A",
      "buy_ratio":             { "1m": null, "3m": null },
      "report_count":          { "1m": 0,    "3m": 0 },
      "source": "naver_crawl",
      "note": "크롤링 실패 시 null 처리 후 논거 생략"
    },
    "as_of": "2026-03-31 15:30"
  },

  "relative_strength": {
    "sector_etf": "091160",
    "rs_history": {
      "1m": { "stock_ret": -2.1, "sector_ret": -0.9, "kospi_ret": -1.5, "rs_vs_sector": -1.2, "rs_vs_kospi": -0.6 },
      "3m": { "stock_ret": -5.8, "sector_ret":  1.5, "kospi_ret":  2.1, "rs_vs_sector": -7.3, "rs_vs_kospi": -7.9 },
      "6m": { "stock_ret":  8.4, "sector_ret":  3.1, "kospi_ret":  4.2, "rs_vs_sector":  5.3, "rs_vs_kospi":  4.2 },
      "1y": { "stock_ret":  2.1, "sector_ret":  2.5, "kospi_ret":  3.8, "rs_vs_sector": -0.4, "rs_vs_kospi": -1.7 }
    },
    "rs_trend":         "지속 약화",
    "sector_issue":     "종목 고유 약세 (섹터는 선방)",
    "strongest_period": "6m"
  },

  "valuation": {
    "current": {
      "base_date": "2026-03-31",
      "per":       36.38,
      "pbr":        3.11,
      "eps":     4950.0,
      "bps":    57951.0,
      "div_yield":  1.2
    },
    "per_band": { "current": 36.38, "min_3y": 10.2, "max_3y": 42.5, "median_3y": 22.1, "pct_3y": 89.0 },
    "pbr_band": { "current":  3.11, "min_3y":  0.8, "max_3y":  3.2, "median_3y":  1.8, "pct_3y": 97.0 },
    "per_label":   "역사적 고평가 구간 (상위 20%)",
    "pbr_label":   "역사적 고평가 구간 (상위 20%)",
    "eps_trend":   "EPS 개선 (YoY)",
    "eps_yoy_chg":  1.323,
    "note":        ""
  }
}
```

### 전달 방식 결정 사항

| 항목 | 결정 | 근거 |
|---|---|---|
| 수급 데이터 단위 | **누적 순매수(억원)** 전달, 일별 배열 미전달 | 불/베어 에이전트는 흐름의 방향과 강도가 필요하지 일별 raw 데이터가 필요하지 않음. 토큰 절약. |
| 수급 기간 | 20일/60일/120일 **3구간 누적** 유지 | 단기·중기·장기 방향 불일치 여부를 에이전트가 논거로 사용 가능 |
| 실적 데이터 | **최근 4분기 절대값 + YoY/QoQ 변화율** | Bull은 QoQ 반등을, Bear는 혼조·고평가를 논거로 사용 |
| 목표주가 데이터 | **수집 실패 시 null + note 필드** | 크롤링 불안정성 대응. 에이전트가 null 체크 후 논거 생략 처리 |

---

## 3. 시장심리 에이전트 출력 스펙

**역할**: V-KOSPI, 외국인 수급, KOSPI 변화율을 종합하여 시장 심리 상태를 점수화한다.

**데이터 소스**: `yfinance` (V-KOSPI `^KSVIX`, KOSPI `^KS11`), `pykrx` (외국인 수급)

**스코어링**: V-KOSPI 40% + 외국인수급 40% + KOSPI변화 20% 가중합

### 출력 JSON

```json
{
  "sentiment_label": "낙관",
  "sentiment_score": 0.67,
  "vkospi": {
    "value": 18.2,
    "change_weekly": -2.3
  },
  "foreign_flow": {
    "net_buy": 3200,
    "trend": "순매수"
  },
  "market_momentum": {
    "kospi_change": 0.012,
    "trend": "상승"
  },
  "risk_signal": {
    "fomo": true,
    "panic": false
  },
  "confidence": 0.74,
  "reason": [
    "외국인 순매수 지속",
    "변동성 감소",
    "시장 상승 흐름"
  ]
}
```

### 전달 방식 결정 사항

| 항목 | 결정 | 근거 |
|---|---|---|
| `risk_signal.fomo` / `risk_signal.panic` | **bool** 유지 | 불/베어가 `if fomo: 탐욕 경고 논거 추가` 형태로 즉시 사용 가능 |
| `sentiment_score` | **0~1 float** | 오케스트레이터 `agreement_score` 계산 시 입력값으로 활용 |
| `confidence` | **0~1 float** | 지표 간 방향 불일치 시 낮아짐. 오케스트레이터가 심리 데이터 비중 조정에 사용 |
| V-KOSPI 일별 배열 | **미전달** | 현재값 + 주간 변화량만 전달. 추세는 `change_weekly` 부호로 판단 가능 |

---

## 4. 에이전트 출력 → 불/베어 입력 매핑

> 각 에이전트의 출력 필드가 불/베어 공통 입력 패키지의 어느 위치에, 어떤 처리를 거쳐 들어가는지 명시한다.
> **"그대로"** = 가공 없이 복사 / **"제외"** = 불/베어에 미전달 (에이전트 내부 분석용)

### 4-1. 매크로 에이전트 출력 → `macro` 필드

| 출력 필드 | 입력 위치 | 처리 | 불(Bull) 활용 | 베어(Bear) 활용 |
|---|---|---|---|---|
| `raw_indicators.market_index.KOSPI` | `macro.raw_indicators.market_index.KOSPI` | 그대로 | 지수 상승·해석 "상승" → 긍정 환경 | 지수 하락·`momentum` "위축" → 약세 근거 |
| `raw_indicators.market_index.USD_KRW` | `macro.raw_indicators.market_index.USD_KRW` | 그대로 | 환율 안정(하락) → 외국인 유입 기대 | 환율 급등(원화 약세) → 자본 유출 우려 |
| `raw_indicators.interest_rates_spread.Term_Spread` | `macro.raw_indicators.interest_rates_spread.Term_Spread` | 그대로 | `status: "정상"`, 양수 유지 → 침체 신호 부재 | 축소·역전 → 경기침체 전조 근거 |
| `raw_indicators.interest_rates_spread.Credit_Spread` | `macro.raw_indicators.interest_rates_spread.Credit_Spread` | 그대로 | 안정 → 기업 자금조달 부담 완화 | 급등(`wow_change_pt` 큰 양수) → 기업 신용위험 증가 |
| `quantitative_models.fsi_factor_score` | `macro.quantitative_models.fsi_factor_score` | 그대로 | 음수(스트레스 낮음) → 안정적 거시 환경 | 양수(스트레스 높음) → 리스크 오프 근거 |
| `quantitative_models.regime_probabilities` | `macro.quantitative_models.regime_probabilities` | 그대로 | `state_0_normal` 우세 → 정상 국면 긍정 근거 | `state_2_crisis` 상승 → 위기 국면 진입 경고 |
| `objective_analysis.current_regime_diagnosis` | `macro.objective_analysis.current_regime_diagnosis` | 그대로 | 낙관 해석의 거시 맥락으로 인용 | 비관 해석의 거시 맥락으로 인용 |
| `objective_analysis.risk_assessment` | `macro.objective_analysis.risk_assessment` | 그대로 | "Low" → 투자 환경 우호적 근거 | "Medium/High" → 투자 위험 부각 근거 |
| `objective_analysis.momentum` | `macro.objective_analysis.momentum` | 그대로 | "개선" → 스트레스 완화 근거 | "위축" → 스트레스 심화 근거 |
| `meta`, `errors` | — | **제외** | — | — |
| `macro_score` (오케스트레이터 전용) | — | `state_0_normal − state_2_crisis` 산출 | 불/베어 직접 미사용 | 불/베어 직접 미사용 → **오케스트레이터 agreement_score 계산에만 사용** |

---

### 4-2. 섹터종목 에이전트 출력 → `sector` 필드

| 출력 필드 | 입력 위치 | 처리 | 불(Bull) 활용 | 베어(Bear) 활용 |
|---|---|---|---|---|
| `supply_demand.20d.foreign` / `60d.foreign` / `120d.foreign` | `sector.supply_demand.20d` 등 | 그대로 (누적값) | 순매수 전환 구간 부각 | 지속 순매도 규모 직접 인용 |
| `supply_demand.streak.foreign_consecutive_sell` | `sector.supply_demand.streak` | 그대로 | 매도 완화 시 반등 기대 근거 | 연속 매도일수 직접 인용 |
| `supply_demand.intensity_change` | `sector.supply_demand.intensity_change` | 그대로 | 심화→완화 흐름이면 긍정 신호 | "매도 강도 심화" 레이블 직접 인용 |
| `earnings.quarters` (dict) | `sector.earnings.quarters` | 그대로 (4분기) | QoQ 반등 분기 부각 | 혼조 추세·불안정 부각 |
| `earnings.yoy.op_income_chg` / `qoq.op_income_chg` | `sector.earnings.yoy` / `qoq` | 그대로 | 높은 QoQ 성장률 근거 | YoY 낮거나 혼조 시 근거 |
| `earnings.trend_3q` | `sector.earnings.trend_3q` | 그대로 | "혼조" → 반등 가능성 부각 | "혼조/악화" 레이블 인용 |
| `naver_finance.analyst_opinion.*` | `sector.naver_finance.analyst_opinion` | 그대로 (null 가능) | 목표주가 상향 시 긍정 근거 | 하향 또는 null → 불확실성 근거 |
| `relative_strength.rs_history.*` | `sector.relative_strength.rs_history` | 그대로 | RS 개선 구간 부각 | RS 약화 추세·종목 고유 이슈 부각 |
| `valuation.current.per` / `pbr` | `sector.valuation.current` | 그대로 | 저평가 구간이면 매수 기회 | 고평가 백분위 직접 인용 |
| `valuation.per_band.pct_3y` / `pbr_band.pct_3y` | `sector.valuation.per_band` / `pbr_band` | 그대로 | 낮은 백분위 → 역사적 저평가 | 높은 백분위 → 역사적 고평가 |
| `valuation.eps_yoy_chg` | `sector.valuation.eps_yoy_chg` | 그대로 | EPS 성장률로 고PER 정당화 | EPS 하락 시 저평가 메리트 희석 근거 |
| 일별 수급 배열 (내부) | — | **제외** | — | — |

---

### 4-3. 시장심리 에이전트 출력 → `sentiment` 필드

| 출력 필드 | 입력 위치 | 처리 | 불(Bull) 활용 | 베어(Bear) 활용 |
|---|---|---|---|---|
| `sentiment_label` | `sentiment.sentiment_label` | 그대로 | "낙관" 시 시장 분위기 우호 근거 | "과열" 시 과매수 경고, "공포" 시 리스크 오프 근거 |
| `sentiment_score` | `sentiment.sentiment_score` | 그대로 | 0.6↑ → 우호적 심리 근거 | 0.8↑ → 과열 경고 근거 |
| `vkospi.value` / `change_weekly` | `sentiment.vkospi` | 그대로 | VIX 하락 → 불안 완화 근거 | VIX 상승 → 불안 심화 근거 |
| `foreign_flow.net_buy` / `trend` | `sentiment.foreign_flow` | 그대로 | 순매수 → 외국인 유입 근거 | 순매도 → 자본 이탈 근거 |
| `market_momentum.kospi_change` | `sentiment.market_momentum` | 그대로 | 상승 추세 확인 근거 | 하락 추세 리스크 근거 |
| `risk_signal.fomo` | `sentiment.risk_signal.fomo` | 그대로 (bool) | fomo=true → 매수 분위기 우호 (선택적) | **fomo=true → 과열 경고 핵심 근거** |
| `risk_signal.panic` | `sentiment.risk_signal.panic` | 그대로 (bool) | **panic=true → 역발상 반등 근거** | panic=true → 공포 심화 근거 |
| `confidence` | `sentiment.confidence` | 그대로 | 불/베어 직접 미사용 | 불/베어 직접 미사용 → **오케스트레이터가 심리 데이터 반영 비중 조정에 사용** |
| `reason[]` | `sentiment.reason` | 그대로 | 우호적 이유 선택 인용 | 부정적 이유 선택 인용 |

---

## 5. 불/베어 공통 입력 패키지

> 불 에이전트와 베어 에이전트는 **동일한 패키지**를 입력받는다.
> 해석 방향은 각 에이전트의 **시스템 프롬프트**로만 분리한다.

```json
{
  "topic": "삼성전자(005930) 지금 매수해도 되나?",
  "topic_type": "종목",

  "technical": {
    "ticker": "005930",
    "name": "삼성전자",
    "date": "2026-03-31",
    "price": 62500,
    "ma_5": 61800, "ma_20": 60200, "ma_60": 58900,
    "ma_120": 57100, "ma_200": 55000,
    "golden_cross_20_60": true,
    "rsi_14": 68.3,
    "macd_signal": "bullish_crossover",
    "bollinger_position": "upper_band_near",
    "disparity_20": 103.8,
    "volume_change_5d": 0.32,
    "support_level": 59000,
    "resistance_level": 64000
  },

  "macro": {
    "raw_indicators": {
      "market_index": {
        "KOSPI":   { "current": 5277.3, "dod_change_pct": 0.0,  "interpretation": "하락" },
        "USD_KRW": { "current": 1513.4, "dod_change_pct": 0.35 }
      },
      "interest_rates_spread": {
        "Term_Spread":   { "current": 0.327, "wow_change_pt": 0.015, "status": "정상" },
        "Credit_Spread": { "current": 0.614, "wow_change_pt": 0.016 }
      }
    },
    "quantitative_models": {
      "fsi_factor_score": -0.6779,
      "regime_probabilities": {
        "state_0_normal":  0.7849,
        "state_1_caution": 0.1518,
        "state_2_crisis":  0.0633
      }
    },
    "objective_analysis": {
      "current_regime_diagnosis": "현재 한국 경기 국면은 정상/안정 (Normal) 상태이며, 해당 국면 진입 확률이 78.5%로 지배적임.",
      "risk_assessment": "투자 환경 위험도는 Low 수준. 장단기 금리차가 0.327%p를 기록하고 있음.",
      "momentum": "위축"
    }
  },

  "sector": {
    "supply_demand": { ... },
    "earnings": { ... },
    "naver_finance": { ... },
    "relative_strength": { ... },
    "valuation": { ... }
  },

  "sentiment": {
    "sentiment_label": "낙관",
    "sentiment_score": 0.67,
    "vkospi": { "value": 18.2, "change_weekly": -2.3 },
    "foreign_flow": { "net_buy": 3200, "trend": "순매수" },
    "market_momentum": { "kospi_change": 0.012, "trend": "상승" },
    "risk_signal": { "fomo": true, "panic": false },
    "confidence": 0.74,
    "reason": ["..."]
  },

  "news_events": {
    "news_available": true,
    "recent_news": [
      { "title": "삼성전자 1분기 실적 예상치 상회", "source": "네이버금융", "date": "2026-03-30" }
    ],
    "recent_disclosures": [
      { "title": "분기보고서 제출", "date": "2026-02-14" }
    ],
    "analyst_report_summary": null
  }
}
```

> ⚠️ **수집 실패 시**: `news_available: false`, `recent_news: []`로 전달.
> 불/베어 에이전트 프롬프트에 다음 조건을 반드시 포함할 것:
> `"news_available이 false인 경우, 뉴스 및 공시 기반 논거는 사용하지 말 것."`
```

---

## 6. 불/베어 시스템 프롬프트 — 데이터 우선순위 지시

> 불/베어 에이전트는 전체 입력 패키지를 받되, 시스템 프롬프트에서 topic_type에 따라 어떤 데이터를 우선적으로 논거로 활용할지 지시한다.
> 이를 통해 토큰 낭비 없이 핵심 신호에 집중한 논거 생성을 유도한다.

```
[시스템 프롬프트 공통 지시]
입력 데이터 전체를 참고하되, topic_type에 따라 아래 우선순위로 논거를 구성하라.
arguments는 최대 3개이며, 우선순위가 높은 데이터 소스에서 먼저 논거를 선택하라.
```

| topic_type | 1순위 | 2순위 | 3순위 |
|---|---|---|---|
| `종목` | technical, sector | sentiment | macro |
| `시장전체` | macro, sentiment | technical | sector |
| `테마` | sector (RS), technical | macro, sentiment | — |

> ⏳ **미결 — 팀 논의 필요**: 위 우선순위가 도메인적으로 적절한지 확인 필요.
> 특히 종목 토론에서 macro를 3순위로 내리는 것이 맞는지 검토 요망.
> (매크로가 전체 시장 방향을 결정하는 큰 그림이므로 1순위 주장도 가능)

---

## 7. 불/베어 에이전트 출력 스펙

### 불 에이전트 출력

```json
{
  "stance": "bullish",
  "confidence": 0.72,
  "arguments": [
    { "claim": "20/60일선 골든크로스 발생으로 중기 추세 전환 신호", "data_ref": "technical.golden_cross_20_60" },
    { "claim": "QoQ 영업이익 +160% 서프라이즈, 실적 모멘텀 회복", "data_ref": "sector.earnings.op_income_qoq" },
    { "claim": "FSI -0.68로 시장 스트레스 낮음, 투자 환경 안정적", "data_ref": "macro.quantitative_models.fsi_factor_score" }
  ],
  "rebuttal": "Bear의 고평가 지적은 EPS +132% 성장률을 반영하지 않은 정적 해석",
  "summary": "실적 서프라이즈 + 기술적 전환 신호로 단기 매수 기회"
}
```

### 베어 에이전트 출력

```json
{
  "stance": "bearish",
  "confidence": 0.68,
  "arguments": [
    { "claim": "RSI 68.3 과매수 구간 진입, 단기 차익실현 압력 증가", "data_ref": "technical.rsi_14" },
    { "claim": "외국인 60일 누적 순매도 -33.3만억원, 수급 구조적 이탈", "data_ref": "sector.supply_demand.60d.foreign" },
    { "claim": "PBR 역사적 97분위, 밸류에이션 부담 과도", "data_ref": "sector.valuation.pbr_band.pct_3y" }
  ],
  "rebuttal": "Bull의 골든크로스는 외국인·기관 동반 매도 심화 속 신뢰도 낮음",
  "summary": "수급 구조적 이탈 + 고평가로 추가 상승 여력 제한적"
}
```

---

## 8. 오케스트레이터 출력 스펙

**Input**: 불 에이전트 출력 + 베어 에이전트 출력 + 매크로 스코어 + 심리 confidence

```json
{
  "verdict": "bearish",
  "agreement_score": "1/3",
  "agreement_level": "약함",
  "conclusion_summary": "실적 모멘텀은 긍정적이나, 수급 구조 이탈과 역사적 고밸류에이션이 단기 리스크를 높인다. 장기 보유 목적이라면 분할 매수 고려, 단기 목적이라면 2~3주 대기 권고.",
  "key_data_points": [
    "외국인 60일 누적 순매도 -333,075억원",
    "PBR 3년 97분위 고평가",
    "RSI 68.3 과매수 구간"
  ],
  "bull_score": 0.72,
  "bear_score": 0.68
}
```

---

## 9. 결정 사항 확정 로그

| # | 항목 | 결정 | 비고 |
|---|---|---|---|
| 0 | `sector_summary` 제거 | ✅ **제거** | LLM 이중 해석 방지. 불/베어가 원본 필드 직접 읽음 |
| 1 | `arguments[].data_ref` 포함 여부 | ✅ **포함** | 근거 추적 가능. 토큰 비용 감수 |
| 2 | 토론 라운드 수 | ⏳ **팀 상의 후 결정** | MVP는 고정 2라운드로 시작 권장. Phase 1 구현 전 확정 필요 |
| 3 | 목표주가 크롤링 실패 시 | ✅ **DART 공시 목표주가로 대체 시도** | 대체도 실패 시 null + note 처리 |
| 4 | 시장 전체 토론 시 `sector` 필드 | ⏳ **Phase 2 때 설계** | 종목 토론 우선 구현. 시장/테마 토론은 `market_topic` 별도 스키마로 분리 예정 |
| 5 | `news_events` 수집 실패 시 | ✅ **수집 실패 플래그 + 뉴스 논거 생략 지시** | 불/베어 에이전트 프롬프트에 "news_available: false 시 뉴스 기반 논거 사용 금지" 조건 추가 필요 |

### 미확정 항목 처리 방침
- **#2 라운드 수**: Claude Code 작업 시작 전 팀 합의 후 이 문서에 업데이트할 것
- **#4 시장 전체 토론 스키마**: Phase 1(종목 토론) 완료 후 별도 설계 세션에서 확정할 것
- **#6 매크로 ammunition 유지 여부 (A안/B안)**: 팀 논의 후 확정. 결정 시 매크로 에이전트 출력 JSON과 Section 4-1 매핑 테이블 함께 수정할 것
- **#7 불/베어 데이터 우선순위**: 도메인 관점에서 종목 토론 시 macro 순위 재검토 필요. 팀 합의 후 Section 6 테이블 업데이트할 것
