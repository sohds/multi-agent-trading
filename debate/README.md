# Debate 모듈

네이버 경제 뉴스를 크롤링하고, GPT로 분석해 **종목토론**과 **테마토론** 주제를 자동 생성하는 모듈입니다.

## 파일 구조

```
debate/
├── debate_topic_agent.py      # 토론 주제 생성 에이전트 (메인)
├── naver_headline_crawler.py  # 네이버 경제 헤드라인 크롤러
└── output/                    # 크롤링 결과 JSON 저장 디렉터리
```

## 동작 흐름

```
네이버 경제 헤드라인 수집
        ↓
cluster_num 내림차순 정렬
        ↓
각 기사 본문 수집 + GPT 분석
        ↓
종목토론 또는 테마토론으로 분류
        ↓
종목토론 1개 + 테마토론 1개 확보 시 종료
        ↓
config/session.json 저장
```

## 모듈 설명

### `naver_headline_crawler.py`

네이버 경제 섹션(`news.naver.com/section/101`)에서 헤드라인 기사를 수집합니다.

**주요 기능:**
- 헤드라인 목록에서 클러스터 기사 수(`cluster_num`) 파싱
- 클러스터 수가 가장 높은 기사를 대표 기사로 선정 (많이 보도될수록 시장 관심도 높음)
- 기사 본문, 발행 시각, 대표 이미지 수집
- 결과를 `output/naver_headline_YYYYMMDD_HHMMSS.json`에 저장

**단독 실행:**
```bash
python debate/naver_headline_crawler.py
```

**반환 구조:**
```json
{
  "title": "기사 제목",
  "url": "기사 URL",
  "press": "언론사",
  "lede": "리드문",
  "cluster_num": 87,
  "body": "기사 본문 전문",
  "published_at": "2026-05-05 10:25:08",
  "image_url": "대표 이미지 URL",
  "all_headlines": [...],
  "crawled_at": "2026-05-05 23:41:32"
}
```

---

### `debate_topic_agent.py`

크롤링된 기사를 GPT로 분석해 투자 토론 주제를 생성하는 메인 에이전트입니다.

**주요 기능:**
- 헤드라인을 `cluster_num` 내림차순으로 순회하며 후보 탐색
- GPT(`gpt-4o-mini`)로 각 기사를 분석해 토론 유형 결정:
  - **종목토론 (stock)**: 특정 상장 종목이 명확한 경우
  - **테마토론 (theme)**: 특정 종목 특정 불가, 산업·섹터·정책 관련인 경우
- 섹터 ETF 매핑 테이블로 관련 ETF 코드 자동 연결
- 기존 세션과 섹터 중복 방지 (다양성 확보)
- 결과를 `config/session.json`에 저장

**단독 실행:**
```bash
python debate/debate_topic_agent.py
```

**섹터 ETF 매핑 (주요 항목):**

| 섹터 | ETF | 코드 |
|------|-----|------|
| 반도체, AI, 인공지능 | KODEX AI코리아액티브 / KODEX 반도체 | 476050 / 091160 |
| 2차전지, 배터리, 전기차 | KODEX 2차전지산업 | 305720 |
| 바이오, 헬스케어, 제약 | KODEX 바이오 | 244580 |
| 방산, 항공, 우주 | TIGER K-방산 | 459580 |
| 조선, 기계 | KODEX 조선 | 139230 |
| 은행, 금융 | KODEX 은행 | 091170 |
| 전력, 원전, 신재생에너지 | KODEX 전력 | 456480 |

전체 매핑 목록은 [debate_topic_agent.py](debate_topic_agent.py)의 `SECTOR_ETF_MAP`을 참조하세요.

---

## 출력 형식 (`config/session.json`)

```json
{
  "stock_debate": {
    "debate_type": "stock",
    "stock_name": "삼성전자",
    "ticker": "005930",
    "sector": "반도체",
    "sector_etf": "091160",
    "debate_topic": "삼성전자(005930) AI 수요 확대로 반도체 업황 반등 기대, 지금 비중 늘릴 타이밍인가?",
    "news": {
      "title": "기사 제목",
      "press": "언론사",
      "url": "기사 URL",
      "cluster_num": 57,
      "lede": "리드문",
      "published_at": "2026-05-05 10:25:08",
      "image_url": "이미지 URL",
      "body": "기사 본문 원문"
    }
  },
  "theme_debate": {
    "debate_type": "theme",
    "stock_name": null,
    "ticker": null,
    "sector": "방산",
    "sector_etf": "459580",
    "debate_topic": "방산(459580) 지정학적 긴장 고조로 수주 확대 기대, 지금 투자 적기인가?",
    "news": { ... }
  },
  "created_at": "2026-05-05 23:41:32"
}
```

## 환경 변수

`.env` 파일에 아래 키가 필요합니다:

```
OPENAI_API_KEY=sk-...
```

## 의존성

```
openai
requests
beautifulsoup4
lxml
python-dotenv
```
