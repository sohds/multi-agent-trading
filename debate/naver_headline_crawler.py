# crawlers/naver_headline_crawler.py
# 실행: python crawlers/naver_headline_crawler.py
#
# 동작 흐름:
#   1. 네이버 경제 섹션(section/101) 접속
#   2. div.section_article.as_headline 내 li._SECTION_HEADLINE 파싱
#   3. 각 li에서 sa_text_cluster_num 추출
#   4. cluster_num 가장 높은 기사 선정
#   5. 선정된 기사 본문 수집

import sys
import io
import os
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional


OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "output")
CONFIG_DIR  = os.path.join(os.path.dirname(__file__), "..", "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "naver_headline.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer":         "https://news.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

SECTION_URL = "https://news.naver.com/section/101"   # 네이버 경제
TODAY_STR   = datetime.today().strftime("%Y-%m-%d")


# ── 유틸 ──────────────────────────────────────────────────────
def _fetch(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"  ⚠️  요청 실패: {url} → {e}")
        return None


def _parse_published_at(soup: BeautifulSoup) -> Optional[datetime]:
    """기사 본문에서 발행 시각 파싱 (data-date-time 속성 우선)"""
    for selector in [
        "._ARTICLE_DATE_TIME",
        ".media_end_head_info_datestamp_time",
        "span.t11",
        "time",
        "em.date",
    ]:
        tag = soup.select_one(selector)
        if not tag:
            continue

        raw = (
            tag.get("data-date-time")
            or tag.get("datetime")
            or tag.get_text(strip=True)
        )
        if not raw:
            continue

        raw = raw.strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y.%m.%d. %H:%M",
            "%Y.%m.%d %H:%M",
        ):
            try:
                return datetime.strptime(raw[:19], fmt)
            except ValueError:
                continue

    return None


# ── STEP 1. 헤드라인 목록 파싱 ───────────────────────────────
def parse_headline_list(soup: BeautifulSoup) -> list[dict]:
    """
    div.section_article.as_headline 내
    li._SECTION_HEADLINE 에서 기사 메타 + cluster_num 수집.

    구조:
      li._SECTION_HEADLINE
        a.sa_text_title           → 기사 URL + 제목
        strong.sa_text_strong     → 제목 텍스트
        div.sa_text_lede          → 본문 요약(리드)
        div.sa_text_press         → 언론사
        span.sa_text_cluster_num  → 클러스터 기사 수
        a.sa_text_cluster         → 클러스터 URL
    """
    headline_section = soup.select_one(
        "div.section_article.as_headline, "
        "div[data-template-id='SECTION_HEADLINE']"
    )
    if not headline_section:
        print("  ⚠️  헤드라인 섹션을 찾을 수 없음")
        return []

    items = []
    for li in headline_section.select("li._SECTION_HEADLINE"):
        # ── 기사 URL + 제목 ───────────────────────────────
        title_tag = li.select_one("a.sa_text_title")
        if not title_tag:
            continue

        article_url = title_tag.get("href", "")
        strong_tag  = li.select_one("strong.sa_text_strong")
        title       = (
            strong_tag.get_text(strip=True)
            if strong_tag
            else title_tag.get_text(strip=True)
        )
        if not title or not article_url:
            continue

        # ── 리드문 ────────────────────────────────────────
        lede_tag = li.select_one("div.sa_text_lede")
        lede     = lede_tag.get_text(strip=True) if lede_tag else ""

        # ── 언론사 ────────────────────────────────────────
        press_tag = li.select_one("div.sa_text_press")
        press     = press_tag.get_text(strip=True) if press_tag else ""

        # ── 클러스터 수 ───────────────────────────────────
        cluster_tag = li.select_one("span.sa_text_cluster_num")
        cluster_num = 0
        if cluster_tag:
            try:
                cluster_num = int(cluster_tag.get_text(strip=True))
            except ValueError:
                pass

        # ── 클러스터 URL ──────────────────────────────────
        cluster_link_tag = li.select_one("a.sa_text_cluster")
        cluster_href     = cluster_link_tag.get("href", "") if cluster_link_tag else ""
        cluster_url      = (
            "https://news.naver.com" + cluster_href
            if cluster_href and cluster_href.startswith("/")
            else cluster_href
        )

        items.append({
            "title":       title,
            "url":         article_url,
            "press":       press,
            "lede":        lede,
            "cluster_num": cluster_num,
            "cluster_url": cluster_url,
        })

    return items


# ── STEP 2. 클러스터 수 최대 기사 선정 ───────────────────────
def select_top_article(items: list[dict]) -> Optional[dict]:
    """cluster_num이 가장 높은 기사 반환"""
    if not items:
        return None
    return max(items, key=lambda x: x["cluster_num"])


# ── STEP 3. 기사 본문 수집 ────────────────────────────────────
def parse_article_body(url: str) -> dict:
    """기사 본문·발행시각·대표이미지 수집"""
    soup = _fetch(url)
    if not soup:
        return {
            "body":         None,
            "published_at": None,
            "image_url":    None,
        }

    # 본문
    body = None
    for selector in [
        "#dic_area",
        "#articleBody",
        ".newsct_article",
        "#news_body_area",
        "article",
    ]:
        tag = soup.select_one(selector)
        if tag:
            for rm in tag.select(
                "script, style, .journalist, .reporter_area, table"
            ):
                rm.decompose()
            body = tag.get_text(separator=" ", strip=True)
            break

    # 발행 시각
    published_dt = _parse_published_at(soup)
    published_at = (
        published_dt.strftime("%Y-%m-%d %H:%M:%S") if published_dt else None
    )

    # 대표 이미지
    og_img    = soup.select_one("meta[property='og:image']")
    image_url = og_img.get("content") if og_img else None

    return {
        "body":         body,
        "published_at": published_at,
        "image_url":    image_url,
    }


# ── STEP 4. 전체 실행 ─────────────────────────────────────────
def crawl() -> Optional[dict]:
    """
    네이버 경제 헤드라인에서 클러스터 수 최다 기사 수집.

    Returns:
        {
            title, url, press, lede,
            cluster_num, cluster_url,
            body, published_at, image_url,
            all_headlines,   # 전체 헤드라인 목록 (비교용)
            crawled_at,
        }
    """
    print(f"\n🔎 네이버 경제 헤드라인 크롤링 시작 ({TODAY_STR})\n")

    soup = _fetch(SECTION_URL)
    if not soup:
        print("  ❌ 섹션 페이지 로드 실패")
        return None

    # ── 헤드라인 목록 파싱 ───────────────────────────────
    items = parse_headline_list(soup)
    if not items:
        print("  ❌ 헤드라인 기사를 찾을 수 없음")
        return None

    print(f"  ✅ 헤드라인 {len(items)}건 파싱 완료\n")

    # ── 전체 목록 출력 ───────────────────────────────────
    print(f"  {'순위':<4} {'클러스터':>6}  {'언론사':<12} 제목")
    print(f"  {'-'*70}")
    for i, item in enumerate(items, start=1):
        mark = "★" if item == max(items, key=lambda x: x["cluster_num"]) else " "
        print(
            f"  {i:<4} {item['cluster_num']:>5}개 {mark} "
            f"{item['press']:<12} {item['title'][:40]}"
        )

    # ── 최다 클러스터 기사 선정 ──────────────────────────
    top = select_top_article(items)
    print(f"\n  ★ 선정 기사: [{top['cluster_num']}개] {top['title']}")
    print(f"  URL: {top['url']}\n")

    # ── 전체 헤드라인 메타(published_at, image_url) + 선정 기사 본문 수집 ──
    print(f"  📄 전체 헤드라인 메타 수집 중 ({len(items)}건)...")
    for i, item in enumerate(items, start=1):
        time.sleep(0.5)
        meta = parse_article_body(item["url"])
        item["published_at"] = meta["published_at"]
        item["image_url"]    = meta["image_url"]
        item["_body"]        = meta["body"]
        print(f"    [{i}/{len(items)}] {item['title'][:35]}")

    for item in items:
        item["body"] = item.pop("_body")

    result = {
        **top,
        "all_headlines": items,
        "crawled_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    print(f"  ✅ 수집 완료 | 발행: {top.get('published_at')}")
    return result


# ── 출력 ──────────────────────────────────────────────────────
def print_result(result: dict) -> None:
    SEP  = "=" * 70
    SEP2 = "-" * 70

    print(f"\n{SEP}")
    print(f"  📰 네이버 경제 헤드라인 — 클러스터 최다 기사")
    print(f"  수집 시각: {result['crawled_at']}")
    print(SEP)
    print(f"  제목      : {result['title']}")
    print(f"  언론사    : {result['press']}")
    print(f"  발행시각  : {result.get('published_at') or 'N/A'}")
    print(f"  클러스터  : {result['cluster_num']}개")
    print(f"  URL       : {result['url']}")
    print(f"\n  리드문:\n    {result.get('lede', '')}")
    print(SEP2)
    body_preview = (result.get("body") or "본문 없음")[:200]
    print(f"\n  본문 미리보기:\n    {body_preview}...")
    print(SEP)


# ── JSON 저장 ─────────────────────────────────────────────────
def save_json(result: dict) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts   = datetime.today().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"naver_headline_{ts}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n  💾 JSON 저장: {path}")
    return path


# ── config 저장 (덮어쓰기) ────────────────────────────────────
def save_config(result: dict) -> str:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  💾 config 저장: {CONFIG_FILE}")
    return CONFIG_FILE


# ── 실행 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    result = crawl()
    if result:
        print_result(result)
        save_config(result)
    else:
        print("❌ 수집 실패")