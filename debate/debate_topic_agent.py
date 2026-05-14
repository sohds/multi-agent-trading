# debate_topic_agent.py
# 동작 흐름:
#   1. 네이버 경제 헤드라인 전체 목록 수집
#   2. cluster_num 내림차순 순회
#   3. 각 기사에서 GPT로 종목토론 또는 테마토론 추출
#      - 종목 특정 가능 → 종목토론 후보
#      - 종목 특정 불가 → 테마토론 후보
#      - null 반환 / ETF 매핑 실패 → 다음 후보
#   4. 종목토론 1개 + 테마토론 1개 확보 시 종료
#   5. config/session.json 에 토론 + 원문 뉴스 데이터 저장

import sys
import io
import os
import re
import json
import time
from datetime import datetime
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from naver_headline_crawler import crawl as crawl_headline, parse_article_body

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SESSION_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "session.json"
)

# ── 섹터 ETF 매핑 테이블 ──────────────────────────────────────
SECTOR_ETF_MAP = {
    # ── 기술 ──────────────────────────────────────────
    "반도체":       "091160",   # KODEX 반도체
    "IT":           "266360",   # KODEX IT
    "소프트웨어":   "266360",   # KODEX IT
    "인터넷":       "266360",   # KODEX IT
    "플랫폼":       "266360",   # KODEX IT
    "게임":         "227550",   # TIGER 미디어컨텐츠
    "AI":           "476050",   # KODEX AI코리아액티브  ← 신규
    "인공지능":     "476050",   # KODEX AI코리아액티브  ← 신규
    "클라우드":     "266360",   # KODEX IT            ← 신규
    "데이터센터":   "476050",   # KODEX AI코리아액티브  ← 신규
    "사이버보안":   "266360",   # KODEX IT            ← 신규

    # ── 2차전지 ───────────────────────────────────────
    "2차전지":      "305720",   # KODEX 2차전지산업
    "배터리":       "305720",   # KODEX 2차전지산업
    "전기차":       "305720",   # KODEX 2차전지산업    ← 신규

    # ── 바이오·헬스 ───────────────────────────────────
    "바이오":       "244580",   # KODEX 바이오
    "헬스케어":     "244580",   # KODEX 바이오
    "제약":         "244580",   # KODEX 바이오
    "의료기기":     "244580",   # KODEX 바이오         ← 신규
    "진단":         "244580",   # KODEX 바이오         ← 신규

    # ── 자동차·모빌리티 ───────────────────────────────
    "자동차":       "091180",   # KODEX 자동차
    "모빌리티":     "091180",   # KODEX 자동차
    "부품":         "091180",   # KODEX 자동차         ← 신규

    # ── 금융 ──────────────────────────────────────────
    "은행":         "091170",   # KODEX 은행
    "금융":         "091170",   # KODEX 은행
    "증권":         "102970",   # KODEX 증권
    "보험":         "140700",   # KODEX 보험
    "핀테크":       "091170",   # KODEX 은행           ← 신규
    "카드":         "091170",   # KODEX 은행           ← 신규

    # ── 부동산·인프라 ─────────────────────────────────  ← 섹션 신규
    "부동산":       "329200",   # TIGER 리츠부동산인프라
    "리츠":         "329200",   # TIGER 리츠부동산인프라
    "인프라":       "329200",   # TIGER 리츠부동산인프라

    # ── 소재 ──────────────────────────────────────────
    "철강":         "117680",   # KODEX 철강
    "화학":         "104530",   # KODEX 화학
    "소재":         "104530",   # KODEX 화학
    "비철금속":     "117680",   # KODEX 철강           ← 신규
    "2차전지소재":  "305720",   # KODEX 2차전지산업    ← 신규
    "양극재":       "305720",   # KODEX 2차전지산업    ← 신규

    # ── 산업재 ────────────────────────────────────────
    "조선":         "139230",   # KODEX 조선
    "방산":         "459580",   # TIGER K-방산
    "항공":         "459580",   # TIGER K-방산
    "우주":         "459580",   # TIGER K-방산
    "건설":         "104520",   # KODEX 건설
    "기계":         "139230",   # KODEX 조선           ← 신규 (중공업 관련)
    "로봇":         "476050",   # KODEX AI코리아액티브  ← 신규

    # ── 에너지·전력 ──────────────────────────────────  ← 전력 신규 추가
    "에너지":       "244620",   # KODEX 에너지화학
    "정유":         "244620",   # KODEX 에너지화학
    "전력":         "456480",   # KODEX 전력           ← 신규
    "원전":         "456480",   # KODEX 전력           ← 신규
    "신재생에너지": "456480",   # KODEX 전력           ← 신규
    "태양광":       "456480",   # KODEX 전력           ← 신규
    "풍력":         "456480",   # KODEX 전력           ← 신규

    # ── 소비재 ────────────────────────────────────────
    "유통":         "266410",   # KODEX 유통
    "식품":         "266410",   # KODEX 유통
    "음식료":       "266410",   # KODEX 유통
    "화장품":       "266410",   # KODEX 유통           ← 신규 (K-뷰티 뉴스 多)
    "뷰티":         "266410",   # KODEX 유통           ← 신규
    "패션":         "266410",   # KODEX 유통           ← 신규
    "의류":         "266410",   # KODEX 유통           ← 신규

    # ── 미디어·엔터 ───────────────────────────────────
    "미디어":       "227550",   # TIGER 미디어컨텐츠
    "엔터":         "227550",   # TIGER 미디어컨텐츠
    "엔터테인먼트": "227550",   # TIGER 미디어컨텐츠
    "콘텐츠":       "227550",   # TIGER 미디어컨텐츠
    "OTT":          "227550",   # TIGER 미디어컨텐츠   ← 신규
    "광고":         "227550",   # TIGER 미디어컨텐츠   ← 신규

    # ── 통신 ──────────────────────────────────────────
    "통신":         "266390",   # KODEX 통신
    "5G":           "266390",   # KODEX 통신           ← 신규
}


# ── GPT 프롬프트 ──────────────────────────────────────────────
def _build_system_prompt() -> str:
    sector_list = ", ".join(SECTOR_ETF_MAP.keys())
    return f"""
You are a Korean stock market analyst. Answer ONLY in JSON. No explanation, no markdown.

Given a Korean news article, extract debate fields for a bull/bear investment debate.
Bull argues to BUY. Bear argues to AVOID. Both argue the same debate_topic.

## Debate Type
- "stock": one specific Korean listed company is the clear subject.
- "theme": industry, sector, policy, or macro trend — no single company stands out.

## Rules
- ticker: 6-digit KRX code.
- sector: must be one of — {sector_list}
- If sector doesn't match or stock is unclear, return null for those fields.
- debate_topic (Korean):
  - Use the news as context, but phrase the topic as a general investment stance question.
  - Do NOT quote the news event literally. Abstract it into an investment judgment.
  - The question must be genuinely arguable from both sides: bull argues BUY, bear argues AVOID.
  - stock format: "{{종목명}}({{코드}}) {{투자 관점 상황 요약}}, {{bull vs bear 대립 질문}}?"
  - theme format: "{{섹터명}} {{투자 관점 상황 요약}}, {{bull vs bear 대립 질문}}?"
  - Do NOT include ETF code in debate_topic.

Return this exact JSON:
{{
  "debate_type": "stock",
  "stock_name": "삼성전자",
  "ticker": "005930",
  "sector": "반도체",
  "debate_topic": "삼성전자(005930) AI 수요 확대로 반도체 업황 반등 기대, 지금 비중 늘릴 타이밍인가?"
}}
"""

SYSTEM_PROMPT = _build_system_prompt()


# ── GPT 분석 ──────────────────────────────────────────────────
def analyze_with_gpt(title: str, body: str) -> Optional[dict]:
    if not body:
        print("  ⚠️  본문 없음 → GPT 분석 스킵")
        return None

    user_prompt = f"기사 제목: {title}\n\n기사 본문:\n{body[:3000]}"

    try:
        print("  🤖 gpt-5.4-mini 분석 중...")
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.1,
            max_completion_tokens=300,
            timeout=30,
        )

        raw = response.choices[0].message.content.strip()
        print(f"  GPT 응답: {raw}")

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"  ❌ JSON 파싱 실패: {e}")
        return None
    except Exception as e:
        print(f"  ❌ GPT 호출 실패: {e}")
        return None


# ── 유틸 ──────────────────────────────────────────────────────
def get_sector_etf(sector: Optional[str]) -> Optional[str]:
    if not sector:
        return None
    for key, etf_code in SECTOR_ETF_MAP.items():
        if key in sector:
            return etf_code
    return None


def _load_existing_sectors() -> set:
    """기존 session.json 의 섹터 목록 반환 (다양성 검사용)"""
    try:
        if os.path.exists(SESSION_PATH):
            with open(SESSION_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            sectors = set()
            for key in ("stock_debate", "theme_debate"):
                s = data.get(key, {}).get("sector")
                if s:
                    sectors.add(s)
            return sectors
    except Exception:
        pass
    return set()


def _fix_theme_topic(topic: str, sector: str, sector_etf: str) -> str:
    """테마토론 debate_topic에 ETF 코드 삽입 (기존 괄호 있으면 교체)"""
    m = re.match(re.escape(sector) + r'(\([^)]*\))?\s*(.*)', topic, re.DOTALL)
    if m:
        return f"{sector}({sector_etf}) {m.group(2)}"
    return f"{sector}({sector_etf}) {topic}"


def _build_debate_entry(
    gpt: dict,
    sector_etf: str,
    headline: dict,
    body_data: dict,
) -> dict:
    """GPT 결과 + 뉴스 원문 → debate entry dict 조합"""
    debate_type = gpt.get("debate_type")
    sector      = gpt.get("sector")
    debate_topic = gpt.get("debate_topic", "")

    # 테마토론은 GPT가 ETF 코드를 모르므로 코드에서 직접 삽입
    if debate_type == "theme" and sector and sector_etf and debate_topic:
        debate_topic = _fix_theme_topic(debate_topic, sector, sector_etf)

    return {
        # 토론 정보
        "debate_type":        debate_type,
        "stock_name":         gpt.get("stock_name"),         # theme 이면 null
        "ticker":             gpt.get("ticker"),             # theme 이면 null
        "sector":             sector,
        "sector_etf":         sector_etf,
        "debate_topic":       debate_topic,
        
        # 원문 뉴스
        "news": {
            "title":        headline.get("title"),
            "press":        headline.get("press"),
            "url":          headline.get("url"),
            "cluster_num":  headline.get("cluster_num"),
            "lede":         headline.get("lede"),
            "published_at": body_data.get("published_at"),
            "image_url":    body_data.get("image_url"),
            "body":         body_data.get("body"),           # 본문 원문 포함
        },
    }


# ── 전체 실행 ─────────────────────────────────────────────────
def run() -> Optional[dict]:
    """
    cluster_num 내림차순으로 후보 순회.
    종목토론 1개 + 테마토론 1개 확보 시 종료.
    """
    # STEP 1. 헤드라인 수집
    headline_data = crawl_headline()
    if not headline_data:
        print("❌ 헤드라인 수집 실패")
        return None

    all_items = headline_data.get("all_headlines", [])
    if not all_items:
        print("❌ 헤드라인 목록 없음")
        return None

    # STEP 2. 내림차순 정렬
    candidates = sorted(all_items, key=lambda x: x["cluster_num"], reverse=True)

    # STEP 3. 기존 세션 섹터 (다양성)
    existing_sectors = _load_existing_sectors()
    if existing_sectors:
        print(f"\n  ℹ️  기존 세션 섹터: {existing_sectors} → 동일 섹터 건너뜀")

    # STEP 4. 결과 버킷
    stock_debate: Optional[dict] = None
    theme_debate: Optional[dict] = None
    current_run_sectors: set = set()

    for rank, candidate in enumerate(candidates):

        # 둘 다 확보되면 즉시 종료
        if stock_debate and theme_debate:
            break

        print(
            f"\n  [{rank + 1}위] 클러스터 {candidate['cluster_num']}개 "
            f"— {candidate['title'][:45]}"
        )

        # 본문 수집
        if rank == 0 and headline_data.get("body"):
            body_data = {
                "body":         headline_data["body"],
                "published_at": headline_data.get("published_at"),
                "image_url":    headline_data.get("image_url"),
            }
        else:
            print("  📄 본문 수집 중...")
            time.sleep(0.8)
            body_data = parse_article_body(candidate["url"])

        # GPT 분석
        gpt = analyze_with_gpt(candidate["title"], body_data.get("body", ""))
        if not gpt:
            print("  ⚠️  GPT 결과 없음 → 다음 후보")
            continue

        debate_type = gpt.get("debate_type")
        sector      = gpt.get("sector")
        sector_etf  = get_sector_etf(sector)

        # 섹터 매핑 실패
        if not sector_etf:
            print(f"  ⚠️  ETF 매핑 없음({sector}) → 다음 후보")
            continue

        # 기존 세션 + 이번 루프에서 이미 확보한 섹터 중복 방지
        used_sectors = existing_sectors | {
            stock_debate["sector"] if stock_debate else None,
            theme_debate["sector"] if theme_debate else None,
        } - {None}

        if sector in used_sectors:
            print(f"  ⚠️  이미 사용된 섹터({sector}) → 다음 후보")
            continue

        entry = _build_debate_entry(gpt, sector_etf, candidate, body_data)

        # ── 종목토론 버킷 ──────────────────────────────────
        if debate_type == "stock":
            if not gpt.get("ticker") or not gpt.get("stock_name"):
                print("  ⚠️  ticker/stock_name null → 다음 후보")
                continue
            if stock_debate is None:
                stock_debate = entry
                print(f"  ✅ 종목토론 확보: {gpt.get('debate_topic')}")
            else:
                print("  ↩️  종목토론 이미 확보 → 스킵")

        # ── 테마토론 버킷 ──────────────────────────────────
        elif debate_type == "theme":
            if theme_debate is None:
                theme_debate = entry
                print(f"  ✅ 테마토론 확보: {gpt.get('debate_topic')}")
            else:
                print("  ↩️  테마토론 이미 확보 → 스킵")

        else:
            print(f"  ⚠️  알 수 없는 debate_type({debate_type}) → 다음 후보")

    if not stock_debate and not theme_debate:
        print("❌ 종목토론·테마토론 모두 추출 실패")
        return None

    return {
        "stock_debate": stock_debate,
        "theme_debate": theme_debate,
        "created_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── 출력 ──────────────────────────────────────────────────────
def _print_debate(label: str, d: Optional[dict]) -> None:
    SEP2 = "-" * 60
    if not d:
        print(f"\n  {label}: 추출 실패")
        return

    print(f"\n  ▸ {label}")
    print(f"    토론 주제  : {d.get('debate_topic')}")
    if d.get("ticker"):
        print(f"    종목       : {d.get('stock_name')}({d.get('ticker')})")
    print(f"    섹터       : {d.get('sector')} / ETF: {d.get('sector_etf')}")
    print(f"    뉴스 제목  : {d['news'].get('title')}")
    print(f"    클러스터   : {d['news'].get('cluster_num')}개")
    print(f"    발행시각   : {d['news'].get('published_at') or 'N/A'}")
    print(SEP2)


def print_result(result: dict) -> None:
    SEP = "=" * 60
    print(f"\n{SEP}")
    print(f"  📊 토론 주제 추출 결과")
    print(f"  추출 시각: {result['created_at']}")
    print(SEP)
    _print_debate("종목토론 (Stock Debate)", result.get("stock_debate"))
    _print_debate("테마토론 (Theme Debate)", result.get("theme_debate"))
    print(SEP)


# ── 세션 저장 ─────────────────────────────────────────────────
def save_session(result: dict) -> str:
    """
    config/session.json 저장.
    토론 정보 + 원문 뉴스 body 포함.
    """
    os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)

    with open(SESSION_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n  📋 세션 저장: {SESSION_PATH}")
    return SESSION_PATH


# ── 실행 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    result = run()
    if result:
        print_result(result)
        save_session(result)
    else:
        print("❌ 분석 실패")