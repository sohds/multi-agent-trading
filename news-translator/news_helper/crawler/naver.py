from __future__ import annotations

from dataclasses import asdict, dataclass
import os
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests


DEFAULT_ECONOMY_URL = "https://news.naver.com/section/101"
HEADLINE_SECTION_SELECTOR = ".section_component.as_section_headline"
HEADLINE_ITEM_SELECTOR = "li._SECTION_HEADLINE, li.sa_item._SECTION_HEADLINE"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

REQUEST_TIMEOUT_SECONDS = 15


class CrawlError(RuntimeError):
    """Raised when a Naver news page cannot be fetched or parsed."""


@dataclass(frozen=True)
class ArticleSummary:
    rank: int
    title: str
    url: str
    press: str | None = None
    lede: str | None = None
    thumbnail_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArticleDetail:
    title: str
    url: str
    body: str
    press: str | None = None
    published_at: str | None = None
    modified_at: str | None = None
    body_length: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fetch_economy_headlines(limit: int = 10, section_url: str | None = None) -> list[ArticleSummary]:
    """Fetch top economy headline summaries from Naver News."""
    url = section_url or os.getenv("NAVER_ECONOMY_URL") or DEFAULT_ECONOMY_URL
    html = _fetch_html(url)
    return parse_economy_headlines(html, base_url=url, limit=limit)


def fetch_article(url: str) -> ArticleDetail:
    """Fetch and parse a Naver News article page."""
    html = _fetch_html(url)
    return parse_article(html, url=url)


def fetch_economy_news(limit: int = 10, section_url: str | None = None) -> list[dict[str, Any]]:
    """Fetch economy headline summaries and each article body."""
    results: list[dict[str, Any]] = []
    for summary in fetch_economy_headlines(limit=limit, section_url=section_url):
        try:
            detail = fetch_article(summary.url)
            results.append({"summary": summary.to_dict(), "article": detail.to_dict(), "error": None})
        except CrawlError as exc:
            results.append({"summary": summary.to_dict(), "article": None, "error": str(exc)})
    return results


def parse_economy_headlines(html: str, base_url: str = DEFAULT_ECONOMY_URL, limit: int = 10) -> list[ArticleSummary]:
    soup = BeautifulSoup(html, "html.parser")
    summaries: list[ArticleSummary] = []
    seen_urls: set[str] = set()

    headline_items = _headline_items(soup)
    if not headline_items:
        raise CrawlError("네이버 경제 헤드라인 영역을 찾지 못했습니다. 페이지 구조가 바뀌었을 수 있습니다.")

    for item in headline_items:
        title_node = item.select_one("a.sa_text_title[href*='/mnews/article/']")
        if title_node is None:
            continue

        url = _absolute_url(title_node.get("href"), base_url)
        if not url or url in seen_urls:
            continue

        title = _clean_text(title_node.get_text(" ", strip=True))
        if not title:
            continue

        press = _optional_text(item.select_one(".sa_text_press"))
        lede = _optional_text(item.select_one(".sa_text_lede"))
        thumbnail_url = _thumbnail_url(item, base_url)

        summaries.append(
            ArticleSummary(
                rank=len(summaries) + 1,
                title=title,
                url=url,
                press=press,
                lede=lede,
                thumbnail_url=thumbnail_url,
            )
        )
        seen_urls.add(url)

        if len(summaries) >= limit:
            break

    if not summaries:
        raise CrawlError("네이버 경제 헤드라인 기사를 찾지 못했습니다. 페이지 구조가 바뀌었을 수 있습니다.")

    return summaries


def _headline_items(soup: BeautifulSoup) -> list[Any]:
    headline_section = soup.select_one(HEADLINE_SECTION_SELECTOR)
    if headline_section is None:
        return []

    items = headline_section.select(HEADLINE_ITEM_SELECTOR)
    if items:
        return items

    return [
        item
        for item in headline_section.select("li.sa_item, div.sa_item_flex")
        if item.select_one("a.sa_text_title[href*='/mnews/article/']")
    ]


def parse_article(html: str, url: str) -> ArticleDetail:
    soup = BeautifulSoup(html, "html.parser")

    title = _first_text(
        soup,
        [
            "h2#title_area",
            "h2.media_end_head_headline",
            "meta[property='og:title']",
        ],
    )

    body_node = soup.select_one("#dic_area") or soup.select_one("article#dic_area") or soup.select_one("#newsct_article")
    if body_node is None:
        raise CrawlError(f"기사 본문을 찾지 못했습니다: {url}")

    for node in body_node.select("script, style, iframe, button"):
        node.decompose()

    body = _clean_body(body_node.get_text("\n", strip=True))
    if not body:
        raise CrawlError(f"기사 본문이 비어 있습니다: {url}")

    press = _press_name(soup)
    published_at, modified_at = _article_dates(soup)

    return ArticleDetail(
        title=title or "제목 없음",
        url=url,
        press=press,
        published_at=published_at,
        modified_at=modified_at,
        body=body,
        body_length=len(body),
    )


def _fetch_html(url: str) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CrawlError(f"페이지 요청에 실패했습니다: {url} ({exc})") from exc

    if not response.text:
        raise CrawlError(f"빈 응답을 받았습니다: {url}")

    return response.text


def _absolute_url(value: str | None, base_url: str) -> str | None:
    if not value:
        return None
    return urljoin(base_url, value)


def _thumbnail_url(item: BeautifulSoup, base_url: str) -> str | None:
    image = item.select_one("img[data-src], img[src]")
    if image is None:
        return None
    return _absolute_url(image.get("data-src") or image.get("src"), base_url)


def _optional_text(node: Any | None) -> str | None:
    if node is None:
        return None
    text = _clean_text(node.get_text(" ", strip=True))
    return text or None


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        node = soup.select_one(selector)
        if node is None:
            continue
        if node.name == "meta":
            text = node.get("content")
        else:
            text = node.get_text(" ", strip=True)
        cleaned = _clean_text(text or "")
        if cleaned:
            return cleaned
    return None


def _press_name(soup: BeautifulSoup) -> str | None:
    logo = soup.select_one("a.media_end_head_top_logo img[alt]")
    if logo and logo.get("alt"):
        return _clean_text(logo["alt"])

    meta = soup.select_one("meta[property='og:article:author']")
    if meta and meta.get("content"):
        return _clean_text(meta["content"])

    return None


def _article_dates(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    nodes = soup.select("span.media_end_head_info_datestamp_time")
    dates: list[str] = []

    for node in nodes:
        value = node.get("data-date-time") or node.get_text(" ", strip=True)
        value = _clean_text(value)
        if value:
            dates.append(value)

    published_at = dates[0] if dates else None
    modified_at = dates[1] if len(dates) > 1 else None
    return published_at, modified_at


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _clean_body(value: str) -> str:
    lines = [_clean_text(line) for line in value.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)
