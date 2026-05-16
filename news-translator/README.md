# News Translator

네이버 경제 뉴스 본문에서 일반 독자가 이해하기 어려운 경제/금융 용어를 자동으로 찾고, 쉬운 설명과 함께 하이라이트하는 웹 서비스입니다.

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

## 동작 흐름

```text
뉴스 기사 본문 입력
→ 룰베이스 사전으로 경제 용어 1차 탐지
→ LLM이 문맥을 보고 추가 어려운 용어 탐지
→ 같은 개념의 다른 표기를 canonical_term 기준으로 병합
→ term_type / highlight_decision / is_minimal_term으로 하이라이트 여부 판단
→ 경계 기반 매칭으로 긴 단어 내부 오탐 방지
→ 난이도 점수에 따라 노랑/주황/빨강 하이라이트 적용
→ 웹 화면에 기사 본문과 용어 설명 표시
```

## 프로젝트 구조

```text
news-translator/
├── data/
│   └── terms_800_preprocessed.json     # 경제 용어 룰베이스 사전
├── news_helper/
│   ├── crawler/                        # 네이버 경제 뉴스 수집
│   ├── llm/                            # 룰베이스 + LLM 분석
│   ├── web/                            # FastAPI API 및 하이라이트 생성
│   ├── cli.py                          # CLI 실행 도구
│   ├── config.py                       # 환경변수 로딩
│   └── text_match.py                   # 경계 기반 용어 매칭
├── static/                             # 웹 UI
├── .env.example
├── README.md
└── run_web.py                          # 웹 서버 실행 진입점
```

## 설치

프로젝트 루트에 `requirements.txt`가 있는 경우:

```powershell
pip install -r requirements.txt
```

`news-translator` 폴더만 따로 사용하는 경우:

```powershell
pip install fastapi "uvicorn[standard]" requests beautifulsoup4 python-dotenv
```

## 환경변수 설정

`news-translator/.env.example`을 참고해 `news-translator/.env` 파일을 만듭니다.

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.4-mini-2026-03-17
DIFFICULTY_THRESHOLD=0.4
NAVER_ECONOMY_URL=https://news.naver.com/section/101
WEB_NEWS_LIMIT=10
LLM_MAX_ARTICLE_CHARS=6000
OPENAI_TIMEOUT_SECONDS=180
OPENAI_MAX_RETRIES=1
DEBUG_LLM=true
```

환경변수는 저장소 루트의 `.env`와 `news-translator/.env`를 모두 읽습니다. 같은 키가 있으면 `news-translator/.env` 값이 우선 적용됩니다.

API 키가 포함된 `.env` 파일은 GitHub에 업로드하지 않아야 합니다.

## 실행

```powershell
cd news-translator
python run_web.py
```

브라우저에서 아래 주소로 접속합니다.

```text
http://127.0.0.1:8000
```

주요 API:

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/` | 웹 UI |
| `POST` | `/api/start` | 최신 경제 뉴스 수집 및 분석 시작 |
| `GET` | `/api/health` | 서버 상태 확인 |

## CLI 사용

```powershell
cd news-translator

# 경제 뉴스 헤드라인 수집
python -m news_helper.cli headlines --limit 5 --pretty

# 기사 본문까지 수집
python -m news_helper.cli crawl --limit 3 --pretty

# 수집과 용어 분석을 함께 실행
python -m news_helper.cli analyze-crawl --limit 1 --pretty

# 특정 기사 URL 분석
python -m news_helper.cli analyze-article "기사_URL" --pretty
```

## 핵심 개선 로직

### 1. 용어 정규화

같은 개념이 여러 표기로 등장하는 문제를 줄이기 위해 결과 구조를 분리했습니다.

| 필드 | 의미 |
| --- | --- |
| `term` | 기사 본문에 실제 등장한 표기 |
| `canonical_term` | 같은 개념을 묶는 대표 용어 |
| `variants` | 약어, 괄호 포함 표기, 동의 표기 |

예를 들어 `CSM`, `보험계약마진`, `보험계약마진(CSM)`은 같은 개념으로 병합될 수 있습니다.

### 2. 룰베이스 + LLM 결합

경제 용어 사전(`data/terms_800_preprocessed.json`)으로 본문에 등장한 용어를 먼저 찾고, 그 결과를 LLM 프롬프트에 함께 전달합니다.

최종 결과에는 용어 출처가 기록됩니다.

| source | 의미 |
| --- | --- |
| `rule` | 룰베이스 사전으로만 찾은 용어 |
| `llm` | LLM이 새로 찾은 용어 |
| `hybrid` | 룰베이스와 LLM 양쪽에서 확인된 용어 |

### 3. 구조적 필터링

단순 금지어 목록이나 길이 제한 대신, LLM이 각 후보의 유형과 하이라이트 여부를 구조화해서 반환하도록 했습니다.

주요 필드:

```text
term_type
highlight_decision
exclude_reason
is_minimal_term
```

하이라이트 조건:

```text
highlight_decision == include
AND is_minimal_term == true
AND term_type이 허용된 경제/실무 용어 유형
```

허용하는 주요 `term_type`:

```text
economic_concept
financial_instrument
policy_or_regulation
indicator
accounting_term
legal_administrative_term
labor_relations_term
business_management_term
industry_technology_term
real_estate_term
insurance_actuarial_term
debt_restructuring_term
```

제외하는 주요 `term_type`:

```text
company_name
person_name
place_name
general_word
sentence_fragment
```

### 4. 부분 문자열 오탐 방지

단순 문자열 검색을 사용하면 `경기지방노동위원회` 안의 `경기`처럼 긴 단어 내부 일부가 잘못 하이라이트될 수 있습니다.

이를 막기 위해 `news_helper/text_match.py`에서 경계 기반 매칭을 사용합니다.

- 앞뒤가 한글/영문/숫자로 바로 이어지면 같은 단어 내부로 보고 제외
- 공백, 문장부호, 괄호 등으로 분리되어 있으면 독립 용어로 인정
- `경기가`, `자본시장과`처럼 한국어 조사가 붙은 경우는 정상 용어로 인정

### 5. LLM 실패 처리

LLM 분석이 실패하면 룰베이스 결과만으로 정상 분석처럼 보여주지 않습니다.

웹 응답에는 해당 기사에 대해 다음과 같은 오류 메시지가 포함됩니다.

```text
LLM 분석에 실패했습니다. 잠시 후 다시 시도해주세요.
```

## 하이라이트 색상

난이도 점수에 따라 다른 색상을 적용합니다.

| difficulty_score | 색상 |
| --- | --- |
| 0.4 이상 0.6 미만 | 노랑 |
| 0.6 이상 0.8 미만 | 주황 |
| 0.8 이상 1.0 이하 | 빨강 |

## 실험 결과 요약

10개 경제 기사와 수동 정답 데이터 162개를 기준으로 1차 baseline과 개선 후 2차 실험을 비교했습니다. 두 실험 모두 `temperature=0`, reasoning 미사용 조건으로 맞췄습니다.

threshold `0.5` 기준:

| 지표 | 1차 baseline | 2차 실험 | 변화 |
| --- | ---: | ---: | ---: |
| TP | 73 | 62 | -11 |
| FP | 102 | 60 | -42 |
| FN | 89 | 100 | +11 |
| Micro Precision | 0.417 | 0.508 | +0.091 |
| Micro Recall | 0.451 | 0.383 | -0.068 |
| Micro F1 | 0.433 | 0.437 | +0.003 |
| Macro F1 | 0.429 | 0.443 | +0.014 |
| Over-highlight Rate | 0.583 | 0.492 | -0.091 |
| Missing Rate | 0.549 | 0.617 | +0.068 |
| 평균 예측 용어 수 | 17.5개/article | 12.2개/article | -5.3개/article |

해석:

- 구조적 필터링으로 과잉 하이라이트와 FP가 크게 줄었습니다.
- Precision은 개선되었지만 Recall은 낮아졌습니다.
- 현재 모델은 "많이 잡고 많이 틀리는 방식"에서 "덜 잡지만 더 정확한 방식"으로 바뀐 상태입니다.
- 다음 개선 방향은 현재 precision을 유지하면서 recall을 회복하는 것입니다.

## 주의사항

- `.env`와 API 키는 GitHub에 커밋하지 마세요.
- `data/debug/openai_api.jsonl`은 LLM 요청 로그이므로 업로드 대상에서 제외하는 것이 좋습니다.
- 네이버 페이지 구조가 바뀌면 크롤러가 수정되어야 할 수 있습니다.
- LLM 결과는 확률적이므로 실험 비교 시 `temperature=0`으로 고정하는 것을 권장합니다.
