from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from news_helper.config import load_env
from news_helper.crawler import CrawlError, fetch_article, fetch_economy_headlines
from news_helper.llm import LlmApiError, analyze_difficult_terms


def main() -> int:
    load_env()

    headline = fetch_economy_headlines(limit=1)[0]
    article = fetch_article(headline.url)
    analysis = analyze_difficult_terms(article_body=article.body, title=article.title)

    payload = {
        "article": article.to_dict(),
        "analysis": analysis.to_dict(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CrawlError, LlmApiError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
