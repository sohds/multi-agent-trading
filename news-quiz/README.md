# 📰 news-quiz

뉴스 기사를 크롤링하여 **AI가 자동으로 경제·투자 OX 퀴즈를 생성**하는 모듈입니다.  
단순 팩트 확인이 아닌, 경제 원리와 시장 인과관계를 묻는 Financial Literacy를 키울 수 있는 퀴즈를 출제합니다.

---

## 📁 폴더 구조

```
multi-agent-trading/
├── .env
├── news-translator/
│   └── news_helper/
│       └── crawler
│           └── naver.py        # 네이버 경제 뉴스 크롤러
└── news-quiz/
    ├── quiz_engine.py          # LLM 기반 퀴즈 생성 로직
    └── cli.py                 # CLI 실행 진입점
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

`news-quiz/` 디렉토리에서 실행합니다.

### 기본 실행 (최신 뉴스 1개)

```bash
python cli.py
```

### 옵션

| 옵션       | 타입 | 기본값  | 설명                           |
| ---------- | ---- | ------- | ------------------------------ |
| `--limit`  | int  | `1`     | 퀴즈를 생성할 뉴스 기사 수     |
| `--output` | str  | 없음    | 결과를 저장할 JSON 파일 경로   |
| `--pretty` | flag | `False` | 퀴즈를 터미널에 보기 좋게 출력 |

### 예시

```bash
# 뉴스 5개를 가져와 터미널에 출력
python cli.py --limit 5 --pretty

# 뉴스 3개를 가져와 JSON 파일로 저장
python cli.py --limit 3 --output data/quizzes.json

# 뉴스 10개를 출력 + 저장 동시에
python cli.py --limit 10 --pretty --output data/quizzes.json
```

---

## 📤 출력 형식

`--output` 옵션 사용 시 아래 구조의 JSON 파일이 생성됩니다.

```json
[
  {
    "title": "HMM, 1분기 영업이익 전년 대비 56% 감소",
    "url": "https://...",
    "quiz": {
      "question": "해상 운임 지수(SCFI)가 지속적으로 하락하면 HMM과 같은 해운사들의 수익성은 일반적으로 개선된다.",
      "answer": "X",
      "explanation": "해상 운임 지수는 선박으로 화물을 운반할 때 받는 운송료 수준을 나타냅니다. 운임이 낮아지면 해운사의 매출이 직접 줄어들기 때문에 수익성은 악화됩니다. 따라서 이번 기사에서 HMM의 영업이익이 크게 감소했던 것도 운임 하락의 영향이 컸습니다."
    }
  }
]
```

---

## 🧠 퀴즈 생성 원칙

`quiz_engine.py`의 LLM 프롬프트는 아래 원칙으로 퀴즈를 설계합니다.

- **정답 'X' 우선 출제 (80% 이상)** — 사람들이 흔히 가지는 경제적 착각과 편견에 관련된 문제를 우선적으로 출제합니다.
- **팩트 체크 금지** — 수치, 날짜, 고유명사를 맞추거나 단순히 뒤바꾸기만 하는 문제는 출제하지 않습니다.
- **인과관계 중심** — "A가 일어나면 B는 어떻게 될까?" 형태의 원리 이해를 묻습니다.
- **2단계 해설** — ① 경제 개념 쉽게 설명 → ② 기사 내용과 자연스럽게 연결합니다.

---

## 🔗 의존 모듈

| 모듈                 | 위치                                           | 역할                      |
| -------------------- | ---------------------------------------------- | ------------------------- |
| `fetch_economy_news` | `news-translator/news_helper/crawler/naver.py` | 네이버 경제 뉴스 크롤링   |
| `generate_ox_quiz`   | `news-quiz/quiz_engine.py`                     | OpenAI API 기반 퀴즈 생성 |
