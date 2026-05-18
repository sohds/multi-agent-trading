# 📰 news-quiz

뉴스 기사를 크롤링하여 **AI가 자동으로 경제·투자 OX 퀴즈를 생성**하는 모듈입니다.

단순 팩트 확인이 아닌, 경제 원리와 시장 인과관계를 묻는 Financial Literacy(금융 문해력)를 키울 수 있는 퀴즈를 출제합니다.

---

## 📁 폴더 구조

```text
multi-agent-trading/
├── debate/
│   └── naver_headline_crawler.py  # 네이버 경제 뉴스 크롤러 (Step 1)
├── news_run_pipeline.py           # ✨ [Main] 전체 프로세스 통합 마스터 파이프라인
│
└── news-quiz/
    ├── quiz_engine.py             # 코어 LLM 기반 퀴즈 생성 로직 (Step 3)
    └── test_quiz.py               # 🧪 [Test] 퀴즈 에이전트 단독 유닛 테스트 스크립트

```

---

## ⚙️ 환경 설정

### 1. 의존성 설치

```bash
pip install openai python-dotenv

```

### 2. 환경변수 설정

프로젝트 루트(`multi-agent-trading/`)에 `.env` 파일을 생성합니다.

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.4-mini   # 생략 시 gpt-4o-mini가 기본값

```

---

## 🚀 실행 방법

운영 목적에 따라 전체 통합 파이프라인 실행과 단독 엔진 테스트(디버깅)로 분리하여 실행합니다.

### 1. 실제 서비스 가동 (통합 파이프라인 실행)

대시보드(UI)에 반영되는 번역 및 퀴즈 데이터 패키지를 일괄 생성하려면 **프로젝트 최상위 루트 디렉토리**에서 마스터 파이프라인을 실행합니다.

```bash
python news_run_pipeline.py

```

### 2. 에이전트 단독 컴포넌트 테스트 (Unit Test)

통합 파이프라인과 별개로, 퀴즈 프롬프트 및 OpenAI API 연동 상태만을 독립적으로 디버깅하고 싶을 때는 `news-quiz/` 디렉토리 내부에서 테스트 스크립트를 가동합니다.

```bash
# 기본 실행 (최신 뉴스 1개 기반 테스트)
python test_quiz.py

# 옵션을 통한 다중 퀴즈 출력 및 테스트용 로컬 JSON 저장
python test_quiz.py --limit 5 --pretty --output test_quizzes.json

```

| 옵션 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `--limit` | int | `1` | 퀴즈를 생성할 테스트 뉴스 기사 수 |
| `--output` | str | 없음 | 테스트 결과를 임시 저장할 JSON 파일 경로 |
| `--pretty` | flag | `False` | 생성된 퀴즈를 터미널 콘솔에 보기 좋게 출력 |

---

## 📤 출력 형식 (통합 패키지 구조)

마스터 파이프라인 및 테스트 결과 성공 시 아래 구조의 UI 최적화 데이터가 생성됩니다.

```json
[
  {
    "article_meta": {
      "title": "\"노사 협상에 주주는 없었다\"…삼성전자 주주단체, 법적 대응 검토",
      "url": "https://n.news.naver.com/mnews/article/008/0005359321",
      "published_at": "2026-05-18 14:59:53",
      "press": "머니투데이",
      "cluster_num": 24,
      "image_url": "https://..."
    },
    "article_body": "...",
    "translated_terms": { ... },
    "quiz": {
      "question": "기업의 성과급을 영업이익의 일정 비율로 자동 연동해 제도화하면, 회사가 이익이 많이 날수록 주주가 가져갈 몫과 미래 투자 재원은 줄어들 수 있으므로 항상 모든 이해관계자에게 동시에 최선의 방식이라고 보기는 어렵다.",
      "answer": "O",
      "explanation": "성과급은 결국 회사가 벌어들인 이익을 어떻게 나눌지 정하는 문제입니다. 이익의 일정 비율을 자동으로 떼어내는 구조는 직원 보상에는 예측 가능성을 주지만, 그만큼 배당이나 설비투자에 쓸 수 있는 재원이 줄어들 수 있습니다. 따라서 이번 기사에서 주주단체가 성과급 제도화를 주주 재산권과 장기 투자 여력의 문제로 본 것입니다."
    }
  }
]

```

---

## 🧠 퀴즈 생성 원칙

`quiz_engine.py`의 LLM 프롬프트는 아래 원칙으로 퀴즈를 설계합니다.

* **정답 'X' 우선 출제 (80% 이상)** — 사람들이 흔히 가지는 경제적 착각과 편견에 관련된 문제를 우선적으로 출제합니다.
* **팩트 체크 금지** — 수치, 날짜, 고유명사를 맞추거나 단순히 뒤바꾸기만 하는 단순 일치 문제는 출제하지 않습니다.
* **인과관계 중심** — "A가 일어나면 B는 어떻게 될까?" 형태의 시장 원리 이해를 묻습니다.
* **2단계 해설** — ① 경제 개념 쉽게 설명 ➡️ ② 기사 이슈 내용과 자연스럽게 연결합니다.

---

## 🔗 에이전트 의존성 연동 구조

| 호출 함수 / 모듈 | 파일 위치 (Path) | 역할 및 책임 |
| --- | --- | --- |
| `crawl` | `debate/naver_headline_crawler.py` | 네이버 경제 섹션 헤드라인 뉴스 및 썸네일/메타 데이터 크롤링 |
| `generate_ox_quiz` | `news-quiz/quiz_engine.py` | 수집된 뉴스 본문 맥락 기반 OpenAI API 연동 OX 퀴즈 및 2단계 해설 생성 |
| `run_daily_news_pipeline` | `news_run_pipeline.py` | 크롤러 ➡️ 번역 에이전트 ➡️ 퀴즈 에이전트 체이닝 및 UI 통합 JSON 패키징 저장 |