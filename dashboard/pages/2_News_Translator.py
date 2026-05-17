"""
뉴스 번역기 — 서비스 페이지

config/naver_headline_*.json의 all_headlines 배열을 뉴스 카드 그리드로 표시합니다.
카드의 '분석 보기' 버튼을 클릭하면 4_News_Detail 페이지로 이동합니다.
"""

import streamlit as st
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.styles import inject_css, sec_title, callout

st.set_page_config(page_title="뉴스 번역기 | AI 주식 브리핑", page_icon="📰", layout="wide")
inject_css()

# 뉴스 카드 버튼: ghost-orange, 소형 글자 (버튼 대비 작은 비율)
st.markdown("""
<style>
/* 분석 보기 버튼: rounded-rect, ghost-orange */
[data-testid="stButton"] > button[kind="primary"] {
    background: #FFFFFF !important;
    color: #EA580C !important;
    border: 1px solid #FED7AA !important;
    border-radius: 10px !important;
    padding: 0.3rem 1.2rem !important;
    min-height: 28px !important;
    letter-spacing: 0.2px !important;
    transition: background 150ms ease, border-color 150ms ease, color 150ms ease !important;
}
[data-testid="stButton"] > button[kind="primary"],
[data-testid="stButton"] > button[kind="primary"] * {
    font-size: 11px !important;
    font-weight: 700 !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #FFF7ED !important;
    border-color: #F97316 !important;
    color: #C2410C !important;
    filter: none !important;
}
/* 원문 → 링크 버튼 */
[data-testid="stLinkButton"] a {
    background: #FFFFFF !important;
    color: #EA580C !important;
    border: 1px solid #FED7AA !important;
    border-radius: 10px !important;
    padding: 0.3rem 1.2rem !important;
    min-height: 28px !important;
    letter-spacing: 0.2px !important;
    transition: background 150ms ease, border-color 150ms ease, color 150ms ease !important;
}
[data-testid="stLinkButton"] a,
[data-testid="stLinkButton"] a * {
    font-size: 11px !important;
    font-weight: 700 !important;
}
[data-testid="stLinkButton"] a:hover {
    background: #FFF7ED !important;
    border-color: #F97316 !important;
    color: #C2410C !important;
    filter: none !important;
}
</style>
""", unsafe_allow_html=True)

# ── 경로 ─────────────────────────────────────
ROOT           = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
HEADLINE_FILE  = os.path.join(ROOT, "config", "naver_headline.json")

# ── 데이터 로드 ───────────────────────────────

def load_headlines() -> list[dict]:
    """
    대표 기사(최상위 키)를 맨 앞에, all_headlines에서 중복 제거 후 최대 10개 반환합니다.
    """
    if not os.path.exists(HEADLINE_FILE):
        return []
    try:
        data = json.load(open(HEADLINE_FILE, encoding="utf-8"))
        top = {k: data.get(k) for k in ["title", "url", "press", "lede",
                                          "cluster_num", "published_at", "image_url", "body"]
               if data.get(k)}
        all_headlines = data.get("all_headlines", [])
        if top.get("url"):
            rest = [h for h in all_headlines if h.get("url") != top["url"]]
            combined = [top] + rest
        else:
            combined = all_headlines
        return combined[:10]
    except Exception:
        return []


# ─────────────────────────────────────────────
headlines = load_headlines()

# ── 헤더 ──────────────────────────────────────
st.markdown("""
<div style="margin-bottom:1.5rem">
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
    letter-spacing:1.2px;color:#7C3AED;margin-bottom:6px">News Translator</div>
    <div style="font-size:28px;font-weight:900;color:#111827">뉴스 번역기</div>
    <div style="font-size:14px;color:#6B7280;margin-top:6px">
        어려운 금융 뉴스를 쉬운 말로 번역합니다. 기사를 클릭해 분석 결과를 확인하세요.
    </div>
</div>
""", unsafe_allow_html=True)

# 상태 strip
crawled_at = "—"
if os.path.exists(HEADLINE_FILE):
    try:
        d = json.load(open(HEADLINE_FILE, encoding="utf-8"))
        crawled_at = d.get("crawled_at", "—")[:16]
    except Exception:
        pass

st.markdown(f"""
<div class="status-strip">
    <div><span class="dot dot-orange"></span>
    <span class="status-v live">뉴스 {len(headlines)}건 준비됨</span></div>
    <span class="sep">|</span>
    <div><span class="status-k">수집 시각 &nbsp;</span><span class="status-v">{crawled_at}</span></div>
    <span class="sep">|</span>
    <div><span class="status-k">번역 엔진 &nbsp;</span><span class="status-v">LLM (연결 대기)</span></div>
</div>
""", unsafe_allow_html=True)

if not headlines:
    callout(
        "📭 수집된 뉴스가 없습니다. "
        "<code>config/naver_headline.json</code> 파일이 존재하는지 확인하세요.",
        kind="warn",
    )
    st.stop()

# ── 뉴스 카드 그리드 ──────────────────────────
sec_title(f"오늘의 헤드라인 ({len(headlines)}건)")


def _card_img(image_url: str, height: int) -> None:
    if image_url:
        st.markdown(
            f'<div style="border-radius:10px 10px 0 0;overflow:hidden;height:{height}px;'
            f'background:#F3F4F6;border:1px solid #E5E7EB;border-bottom:none">'
            f'<img src="{image_url}" referrerpolicy="no-referrer" crossorigin="anonymous"'
            f' style="width:100%;height:{height}px;object-fit:cover"'
            f' onerror="this.parentElement.innerHTML=\'<div style=&quot;height:{height}px;'
            f'display:flex;align-items:center;justify-content:center;font-size:30px;'
            f'opacity:.2&quot;>📰</div>\'">'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="border-radius:10px 10px 0 0;height:{height}px;background:#F3F4F6;'
            f'border:1px solid #E5E7EB;border-bottom:none;display:flex;align-items:center;'
            f'justify-content:center;font-size:30px;opacity:.25">📰</div>',
            unsafe_allow_html=True,
        )


def _card_body(article: dict, show_lede: bool, min_h: int) -> None:
    title   = article.get("title", "제목 없음")
    press   = article.get("press", "")
    pub     = (article.get("published_at") or "")[:10]
    lede    = article.get("lede", "")
    cluster = article.get("cluster_num", 0)

    cluster_tag = ""
    if cluster and cluster > 50:
        cluster_tag = f'<span class="news-cluster">🔥 클러스터 {cluster}건</span>'
    elif cluster:
        cluster_tag = f'<span class="news-cluster">📊 클러스터 {cluster}건</span>'

    lede_html = (
        f'<div style="font-size:12px;color:#6B7280;line-height:1.6;margin-bottom:6px;'
        f'display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">'
        f'{lede}</div>'
        if show_lede and lede else ""
    )

    st.markdown(
        f'<div style="background:#FFFFFF;border:1px solid #E5E7EB;border-top:none;'
        f'border-radius:0 0 10px 10px;padding:12px 12px 8px;min-height:{min_h}px">'
        f'<div style="font-size:10.5px;color:#9CA3AF;margin-bottom:4px">'
        f'<strong style="color:#6B7280">{press}</strong>{(" · " + pub) if pub else ""}</div>'
        f'<div style="font-size:13px;font-weight:700;color:#111827;line-height:1.5;'
        f'margin-bottom:6px;display:-webkit-box;-webkit-line-clamp:3;'
        f'-webkit-box-orient:vertical;overflow:hidden">{title}</div>'
        f'{lede_html}{cluster_tag}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _card_btns(article: dict, idx: int) -> None:
    url = article.get("url", "")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if url:
        # 우측 정렬: spacer(2) + 분석(1) + 원문(1)
        _, b1, b2 = st.columns([2, 1, 1])
        with b1:
            if st.button("분석 보기", key=f"detail_{idx}", use_container_width=True, type="primary"):
                st.session_state.selected_article_for_detail = article
                st.switch_page("pages/4_News_Detail.py")
        with b2:
            st.link_button("원문 →", url, use_container_width=True)
    else:
        _, b1 = st.columns([3, 1])
        with b1:
            if st.button("분석 보기", key=f"detail_{idx}", use_container_width=True, type="primary"):
                st.session_state.selected_article_for_detail = article
                st.switch_page("pages/4_News_Detail.py")


# ─ 2열 × 5행 균일 카드 그리드 ─────────────────
for row_start in range(0, len(headlines), 2):
    row_items = headlines[row_start:row_start + 2]
    cols = st.columns(2)
    for col_idx, article in enumerate(row_items):
        idx = row_start + col_idx
        with cols[col_idx]:
            _card_img(article.get("image_url", ""), height=160)
            _card_body(article, show_lede=True, min_h=100)
            _card_btns(article, idx)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ── 안내 ─────────────────────────────────────
st.divider()
callout(
    "번역 기능은 <code>news-translator/</code> 모듈 연동 후 활성화됩니다. "
    "현재는 뉴스 카드 UI와 분석 결과 레이아웃을 확인할 수 있습니다.",
    kind="orange",
)
