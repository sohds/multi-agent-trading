from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import time
import traceback

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from news_helper.config import get_float_env, load_env
from news_helper.crawler import CrawlError, fetch_economy_news
from news_helper.llm import LlmApiError, analyze_difficult_terms
from news_helper.web.highlight import build_highlight_segments


BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
LATEST_ANALYSIS_PATH = DATA_DIR / "web_latest_analysis.json"
WEB_ERROR_LOG_PATH = DATA_DIR / "debug" / "web_errors.jsonl"
DEFAULT_WEB_NEWS_LIMIT = 10


load_env()

app = FastAPI(title="Economy News Helper")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/start")
def start_analysis() -> dict[str, Any]:
    try:
        result = analyze_latest_news(limit=_web_news_limit())
    except CrawlError as exc:
        _log_web_error(exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        _log_web_error(exc)
        raise HTTPException(
            status_code=500,
            detail=f"서버 내부 오류가 발생했습니다: {type(exc).__name__}: {exc}",
        ) from exc

    _save_latest_result(result)
    return result


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def analyze_latest_news(limit: int = DEFAULT_WEB_NEWS_LIMIT) -> dict[str, Any]:
    threshold = get_float_env("DIFFICULTY_THRESHOLD", 0.4)
    crawled_items = fetch_economy_news(limit=limit)
    analyzed_articles: list[dict[str, Any]] = []

    for item in crawled_items:
        article = item.get("article")
        if not article:
            analyzed_articles.append({**item, "analysis": None, "segments": []})
            continue

        try:
            analysis = analyze_difficult_terms(
                article_body=article["body"],
                title=article.get("title"),
                threshold=threshold,
            )
            analysis_payload = analysis.to_dict()
            analyzed_articles.append(
                {
                    **item,
                    "analysis": analysis_payload,
                    "analysis_error": None,
                    "segments": build_highlight_segments(article["body"], analysis.difficult_terms),
                }
            )
        except LlmApiError as exc:
            analyzed_articles.append(
                {
                    **item,
                    "analysis": None,
                    "analysis_error": f"LLM 분석에 실패했습니다. 잠시 후 다시 시도해주세요. ({exc})",
                    "segments": [{"text": article["body"]}],
                }
            )

    return {
        "threshold": threshold,
        "count": len(analyzed_articles),
        "articles": analyzed_articles,
    }


def _web_news_limit() -> int:
    raw_value = get_float_env("WEB_NEWS_LIMIT", float(DEFAULT_WEB_NEWS_LIMIT))
    return max(1, min(10, int(raw_value)))


def _save_latest_result(result: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_ANALYSIS_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _log_web_error(exc: Exception) -> None:
    WEB_ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback": traceback.format_exc(),
    }
    with WEB_ERROR_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
