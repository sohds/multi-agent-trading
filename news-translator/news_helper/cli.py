from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from news_helper.config import load_env
from news_helper.crawler import CrawlError, fetch_article, fetch_economy_headlines, fetch_economy_news
from news_helper.llm import LlmApiError, analyze_difficult_terms


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    load_env()

    parser = argparse.ArgumentParser(description="Naver economy news helper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    headlines = subparsers.add_parser("headlines", help="Fetch Naver economy headline list")
    headlines.add_argument("--limit", type=int, default=5)
    headlines.add_argument("--pretty", action="store_true")
    headlines.add_argument("--output", type=Path)

    article = subparsers.add_parser("article", help="Fetch a single Naver news article")
    article.add_argument("url")
    article.add_argument("--pretty", action="store_true")
    article.add_argument("--output", type=Path)

    crawl = subparsers.add_parser("crawl", help="Fetch headline list and article bodies")
    crawl.add_argument("--limit", type=int, default=5)
    crawl.add_argument("--pretty", action="store_true")
    crawl.add_argument("--output", type=Path)

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

    if args.command == "headlines":
        payload: Any = [item.to_dict() for item in fetch_economy_headlines(limit=args.limit)]
    elif args.command == "article":
        payload = fetch_article(args.url).to_dict()
    elif args.command == "crawl":
        payload = fetch_economy_news(limit=args.limit)
    elif args.command == "analyze-article":
        article_payload = fetch_article(args.url).to_dict()
        analysis_payload = analyze_difficult_terms(
            article_body=article_payload["body"],
            title=article_payload["title"],
            threshold=args.threshold,
        ).to_dict()
        payload = {"article": article_payload, "analysis": analysis_payload}
    elif args.command == "analyze-crawl":
        payload = _analyze_crawled_items(fetch_economy_news(limit=args.limit), threshold=args.threshold)
    elif args.command == "analyze-file":
        payload = _analyze_crawled_items(_read_json_file(args.path), threshold=args.threshold)
    else:
        parser.error("Unknown command")

    _emit_json(payload, pretty=args.pretty, output=args.output)
    return 0


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
    if isinstance(items, dict) and "article" in items:
        items = [items]
    if not isinstance(items, list):
        raise ValueError("분석 대상 JSON은 crawl 명령의 리스트 형식이어야 합니다.")

    results: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        article = item.get("article")
        if not article:
            results.append({**item, "analysis": None})
            continue

        analysis = analyze_difficult_terms(
            article_body=article["body"],
            title=article.get("title"),
            threshold=threshold,
        )
        results.append({**item, "analysis": analysis.to_dict()})

    return results


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CrawlError, LlmApiError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
