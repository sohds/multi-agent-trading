# 📰 news-translator (뉴스 번역 엔진)

네이버 경제 뉴스 본문에서 일반 독자가 이해하기 어려운 경제/금융 용어를 자동으로 찾고, 쉬운 설명과 함께 하이라이트하는 웹 서비스입니다.

> 🚀 **아키텍처 업데이트:** > 본 모듈은 기존의 독립된 웹 서비스에서 **'AI 주식 브리핑 멀티에이전트 시스템'의 핵심 번역 엔진으로 완벽하게 통합**되었습니다. 중복되던 크롤링 로직을 `debate` 모듈의 통합 크롤러로 일원화하였으며, 현재 실제 서비스 구동은 최상위 폴더의 마스터 파이프라인(`news_run_pipeline.py`) 및 Streamlit 대시보드를 통해 이루어집니다.

이 프로젝트에서 말하는 "번역"은 외국어 번역이 아니라, 경제 기사에 등장하는 전문 용어를 일반 사용자가 이해할 수 있는 표현으로 풀어주는 것을 의미합니다.

## 주요 기능

- 네이버 경제 뉴스 헤드라인과 기사 본문 수집
- 경제 용어 룰베이스 사전 기반 1차 용어 탐지
- LLM 기반 문맥 분석으로 추가 어려운 용어 탐지
- `term`, `canonical_term`, `variants` 기반 중복 용어 통합
- `term_type`, `highlight_decision`, `is_minimal_term` 기반 구조적 필터링
- 단어 내부 부분 문자열 오탐 방지
- 난이도 점수에 따른 하이라이트 색상 표시
- FastAPI 기반 웹 UI 제공

## 🔄 동작 흐름 (파이프라인)

```text
뉴스 기사 본문 입력 (from debate 통합 크롤러)
→ 룰베이스 사전으로 경제 용어 1차 탐지
→ LLM이 문맥을 보고 추가 어려운 용어 탐지
→ 같은 개념의 다른 표기를 canonical_term 기준으로 병합
→ term_type / highlight_decision / is_minimal_term으로 하이라이트 여부 판단
→ 경계 기반 매칭으로 긴 단어 내부 오탐 방지
→ 난이도 점수 부여 후 통합 JSON 패키징 (UI 대시보드 연동)

```

## 📁 프로젝트 구조

```text
news-translator/
├── data/
│   └── terms_800_preprocessed.json     # 경제 용어 룰베이스 사전
├── news_helper/
│   ├── llm/                            # 룰베이스 + LLM 분석 코어 로직
│   ├── web/                            # [Test] FastAPI API 및 하이라이트 생성
│   ├── test_translator.py              # 🧪 [Test] 에이전트 단독 CLI 테스트 스크립트 (구 cli.py)
│   ├── config.py                       # 환경변수 로딩
│   └── text_match.py                   # 경계 기반 용어 매칭
├── static/                             # [Test] 로컬 테스트용 웹 UI
├── .env.example
├── README.md
└── run_web.py                          # [Test] 로컬 테스트용 웹 서버 실행 진입점

```

## ⚙️ 환경변수 설정

프로젝트 최상위 루트 폴더의 `.env`를 공유하여 사용합니다. (필요시 `news-translator/.env` 구성 가능)

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.4-mini-2026-03-17
DIFFICULTY_THRESHOLD=0.4
WEB_NEWS_LIMIT=10
LLM_MAX_ARTICLE_CHARS=6000
OPENAI_TIMEOUT_SECONDS=180
OPENAI_MAX_RETRIES=1
DEBUG_LLM=true

```

## 🚀 실행 방법

운영 목적에 따라 전체 파이프라인 통합 실행과 컴포넌트 단위 단독 테스트로 나뉩니다.

### 1. 실제 서비스 가동 (통합 파이프라인)

대시보드에 반영되는 번역 데이터를 생성하려면 **프로젝트 최상위 루트 디렉토리**에서 실행합니다.

```powershell
python news_run_pipeline.py

```

### 2. 에이전트 단독 유닛 테스트 (CLI)

통합 시스템과 독립적으로 번역 엔진의 프롬프트나 룰베이스 로직만을 디버깅할 때 사용합니다. (`news-translator/` 폴더 내부에서 실행)

```powershell
# 경제 뉴스 헤드라인 수집 (통합 크롤러 연동 테스트)
python news_helper/test_translator.py headlines --limit 5 --pretty

# 수집과 용어 분석을 함께 실행
python news_helper/test_translator.py analyze-crawl --limit 1 --pretty

# 특정 기사 URL 단독 분석
python news_helper/test_translator.py analyze-article "기사_URL" --pretty

```

### 3. (옵션) 기존 웹 UI 단독 테스트

Streamlit 대시보드 통합 이전의 순수 FastAPI 기반 하이라이트 UI를 로컬에서 테스트합니다.

```powershell
python run_web.py
# 브라우저 접속: [http://127.0.0.1:8000](http://127.0.0.1:8000)

```

---

## 🧠 핵심 개선 로직

### 1. 용어 정규화

같은 개념이 여러 표기로 등장하는 문제를 줄이기 위해 결과 구조를 분리했습니다.

| 필드 | 의미 |
| --- | --- |
| `term` | 기사 본문에 실제 등장한 표기 |
| `canonical_term` | 같은 개념을 묶는 대표 용어 |
| `variants` | 약어, 괄호 포함 표기, 동의 표기 |

예를 들어 `CSM`, `보험계약마진`, `보험계약마진(CSM)`은 같은 개념으로 병합될 수 있습니다.

### 2. 룰베이스 + LLM 하이브리드 결합

경제 용어 사전(`data/terms_800_preprocessed.json`)으로 본문에 등장한 용어를 먼저 찾고, 그 결과를 LLM 프롬프트에 함께 전달하여 시너지를 냅니다.

| source | 의미 |
| --- | --- |
| `rule` | 룰베이스 사전으로만 찾은 용어 |
| `llm` | LLM이 새로 찾은 용어 |
| `hybrid` | 룰베이스와 LLM 양쪽에서 확인된 용어 |

### 3. 구조적 필터링

단순 금지어 목록이나 길이 제한 대신, LLM이 각 후보의 유형과 하이라이트 여부를 **구조화된 JSON 형식**으로 반환하도록 제어합니다.

* **하이라이트 조건:** `highlight_decision == include` AND `is_minimal_term == true` AND `term_type`이 허용된 경제/실무 용어 유형
* **제외 대상:** `company_name`, `person_name`, `place_name`, `general_word` 등

### 4. 부분 문자열 오탐 방지

단순 문자열 검색을 사용하면 `경기지방노동위원회` 안의 `경기`처럼 긴 단어 내부 일부가 잘못 하이라이트될 수 있습니다. 이를 막기 위해 `news_helper/text_match.py`에서 경계 기반 매칭(Boundary Matching)을 사용합니다.

* 앞뒤가 한글/영문/숫자로 바로 이어지면 같은 단어 내부로 보고 제외
* 공백, 문장부호, 괄호 등으로 분리되어 있으면 독립 용어로 인정
* `경기가`, `자본시장과`처럼 한국어 조사가 붙은 경우는 정상 용어로 인정

### 5. LLM 실패에 대한 안전장치 (Fail-safe)

LLM 분석이 실패하거나 Timeout이 발생할 경우, 룰베이스 결과만으로 억지 분석을 진행하지 않고 명확한 에러 로그 및 UI 피드백을 반환하여 데이터 오염을 방지합니다.

---

## 📊 실험 결과 요약 (A/B Test)

10개 경제 기사와 수동 정답 데이터 162개를 기준으로 1차 baseline과 개선 후 2차 실험을 비교했습니다. (조건: `temperature=0`, reasoning 미사용)

threshold `0.5` 기준:

| 지표 | 1차 baseline | 2차 실험 (구조화 필터) | 변화 |
| --- | --- | --- | --- |
| TP | 73 | 62 | -11 |
| FP | 102 | 60 | -42 |
| FN | 89 | 100 | +11 |
| Micro Precision | 0.417 | **0.508** | **+0.091** |
| Micro Recall | 0.451 | 0.383 | -0.068 |
| Micro F1 | 0.433 | 0.437 | +0.003 |
| Over-highlight Rate | 0.583 | **0.492** | **-0.091** |
| 평균 예측 용어 수 | 17.5개/article | 12.2개/article | -5.3개/article |


```