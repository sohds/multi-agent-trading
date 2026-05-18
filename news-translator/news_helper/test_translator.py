from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# ── 1. [퀴즈 코드 검증 로직 이식] 상위 폴더(multi-agent-trading) 경로 설정 ──
BASE_DIR = Path(__file__).resolve().parent.parent.parent # news_helper의 parent(2) -> parent(1) -> 루트

# ── 2. 파이썬 경로 패스 선제 등록 ─────────────────────────────────
DEBATE_DIR = BASE_DIR / "debate"
TRANSLATOR_DIR = BASE_DIR / "news-translator"
HELPER_DIR = Path(__file__).resolve().parent

sys.path.append(str(DEBATE_DIR))       # 1. 통합 크롤러가 있는 debate 폴더 추가
sys.path.append(str(TRANSLATOR_DIR))   # 2. news_helper 패키지를 찾을 수 있도록 추가
sys.path.append(str(HELPER_DIR))       # 3. 로컬 내부 임포트용 추가

# ── 3. 패스가 완벽히 등록된 후 에이전트 및 라이브러리 임포트 ────────────────
import requests
from bs4 import BeautifulSoup

try:
    from naver_headline_crawler import crawl, parse_article_body
except Exception as e:
    print("❌ 통합 크롤러 모듈을 찾을 수 없습니다. 경로 또는 패키지를 확인해주세요.")
    print(f"🔍 상세 에러: {e}")
    sys.exit(1)

from news_helper.config import load_env
from news_helper.llm import LlmApiError, analyze_difficult_terms


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    load_env()

    parser = argparse.ArgumentParser(description="Naver economy news helper CLI (Integrated)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    headlines = subparsers.add_parser("headlines", help="Fetch Naver economy headline list")
    headlines.add_argument("--limit", type=int, default=5)
    headlines.add_argument("--pretty", action="store_true")
    headlines.add_argument("--output", type=Path)

    article = subparsers.add_parser("article", help="Fetch a single Naver news article")
    article.add_argument("url")
    article.add_argument("--pretty", action="store_true")
    article.add_argument("--output", type=Path)

    crawl_parser = subparsers.add_parser("crawl", help="Fetch headline list and article bodies")
    crawl_parser.add_argument("--limit", type=int, default=5)
    crawl_parser.add_argument("--pretty", action="store_true")
    crawl_parser.add_argument("--output", type=Path)

    analyze_article = subparsers.add_parser("analyze-article", help="Fetch one article and analyze difficult terms")
    analyze_article.add_argument("url")
    analyze_article.add_argument("--pretty", action="store_true")
    analyze_article.add_argument("--output", type=Path)
    analyze_article.add_argument("--threshold", type=float)

    analyze_crawl = subparsers.add_parser("analyze-crawl", help="Fetch Naver economy articles and analyze difficult terms")
    analyze_crawl.add_argument("--limit", type=int, default=1)
    analyze_crawl.add_argument("--pretty", action="store_true")
    analyze_crawl.add_argument("--output", type=Path)
    analyze_crawl.add_argument("--threshold", type=float)

    analyze_file = subparsers.add_parser("analyze-file", help="Analyze article JSON from a crawler output file")
    analyze_file.add_argument("path", type=Path)
    analyze_file.add_argument("--pretty", action="store_true")
    analyze_file.add_argument("--output", type=Path)
    analyze_file.add_argument("--threshold", type=float)

    args = parser.parse_args()

    # ── 커맨드 매핑 로직 (New 크롤러 연동) ───────────────────────────────────
    if args.command == "headlines":
        crawl_result = crawl()
        payload: Any = crawl_result["all_headlines"][:args.limit] if crawl_result else []
        
    elif args.command == "article":
        payload = _fetch_single_article_with_title(args.url)
        
    elif args.command == "crawl":
        crawl_result = crawl()
        payload = crawl_result["all_headlines"][:args.limit] if crawl_result else []
        
    elif args.command == "analyze-article":
        article_payload = _fetch_single_article_with_title(args.url)
        analysis_obj = analyze_difficult_terms(
            article_body=article_payload["body"],
            title=article_payload["title"],
            threshold=args.threshold,
        )
        analysis_payload = analysis_obj.to_dict() if hasattr(analysis_obj, "to_dict") else analysis_obj
        payload = {"article": article_payload, "analysis": analysis_payload}
        
    elif args.command == "analyze-crawl":
        crawl_result = crawl()
        articles = crawl_result["all_headlines"][:args.limit] if crawl_result else []
        payload = _analyze_crawled_items(articles, threshold=args.threshold)
        
    elif args.command == "analyze-file":
        payload = _analyze_crawled_items(_read_json_file(args.path), threshold=args.threshold)
        
    else:
        parser.error("Unknown command")

    _emit_json(payload, pretty=args.pretty, output=args.output)
    return 0


def _fetch_single_article_with_title(url: str) -> dict[str, Any]:
    """단독 URL 조회 시 제목 파싱을 보완하여 기사 데이터 객체를 빌드합니다."""
    meta = parse_article_body(url)
    title = "제목 미상"
    
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            title_tag = soup.select_one("h2.media_end_head_headline, h2#title_area, h3#articleTitle")
            if title_tag:
                title = title_tag.get_text(strip=True)
    except Exception:
        pass

    return {
        "title": title,
        "url": url,
        "body": meta.get("body"),
        "published_at": meta.get("published_at"),
        "image_url": meta.get("image_url")
    }


def _emit_json(payload: Any, pretty: bool = False, output: Path | None = None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {output}")
        return

    print(text)


def _read_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _analyze_crawled_items(items: Any, threshold: float | None = None) -> list[dict[str, Any]]:
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise ValueError("분석 대상 JSON은 리스트 형식이어야 합니다.")

    results: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        if "body" in item:
            body = item.get("body")
            title = item.get("title")
        elif "article" in item and isinstance(item["article"], dict):
            body = item["article"].get("body")
            title = item["article"].get("title")
        else:
            results.append({**item, "analysis": None})
            continue

        if not body:
            results.append({**item, "analysis": None})
            continue

        analysis = analyze_difficult_terms(
            article_body=body,
            title=title,
            threshold=threshold,
        )
        analysis_payload = analysis.to_dict() if hasattr(analysis, "to_dict") else analysis
        results.append({**item, "analysis": analysis_payload})

    return results


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (LlmApiError, ValueError, Exception) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)