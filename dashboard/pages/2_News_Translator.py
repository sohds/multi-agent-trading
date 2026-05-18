"""
뉴스 번역기 — 서비스 페이지
가장 최신 integrated_news_*.json 파일을 읽어와 뉴스 카드 그리드로 표시합니다.
"""

import streamlit as st
import json
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.styles import inject_css, sec_title, callout

st.set_page_config(page_title="뉴스 번역기 | AI 주식 브리핑", page_icon="📰", layout="wide")
inject_css()

# (기존 CSS 스타일 코드는 그대로 유지하셔도 됩니다)
st.markdown("""
<style>
/* ... (기존 CSS 코드 유지) ... */
</style>
""", unsafe_allow_html=True)

# ── 경로 ─────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
NEWS_OUTPUT_DIR = os.path.join(ROOT, "output", "news")

# ── 최신 통합 데이터 로드 ───────────────────────────────
def load_latest_integrated_news() -> list[dict]:
    if not os.path.exists(NEWS_OUTPUT_DIR):
        return []
    
    # 해당 폴더에서 가장 최근에 생성된 파일 찾기
    files = glob.glob(os.path.join(NEWS_OUTPUT_DIR, "integrated_news_*.json"))
    if not files:
        return []
    
    latest_file = max(files, key=os.path.getctime)
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

headlines = load_latest_integrated_news()

# ── 헤더 ──────────────────────────────────────
st.markdown("""
<div style="margin-bottom:1.5rem">
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
    letter-spacing:1.2px;color:#7C3AED;margin-bottom:6px">News Translator</div>
    <div style="font-size:28px;font-weight:900;color:#111827">뉴스 번역기 & 퀴즈</div>
    <div style="font-size:14px;color:#6B7280;margin-top:6px">
        어려운 금융 뉴스를 쉬운 말로 번역하고, 하단에서 투자 퀴즈를 풀어보세요.
    </div>
</div>
""", unsafe_allow_html=True)

if not headlines:
    callout("📭 수집된 뉴스가 없습니다. 백엔드 파이프라인을 먼저 실행해주세요.", kind="warn")
    st.stop()

# ── 뉴스 카드 그리드 ──────────────────────────
sec_title(f"오늘의 핵심 경제 뉴스 ({len(headlines)}건)")

def _card_body(article: dict, min_h: int) -> None:
    meta = article.get("article_meta", {})
    title   = meta.get("title", "제목 없음")
    press   = meta.get("press", "")
    pub     = (meta.get("published_at") or "")[:10]
    cluster = meta.get("cluster_num", 0)
    
    # 통합 JSON에는 lede가 없으므로 본문 앞부분을 요약으로 씁니다
    body_text = article.get("article_body", "")
    lede = body_text[:80] + "..." if len(body_text) > 80 else body_text

    cluster_tag = ""
    if cluster and cluster > 50:
        cluster_tag = f'<span class="news-cluster" style="color:#F97316;font-weight:600;font-size:11px">🔥 클러스터 {cluster}건</span>'
    elif cluster:
        cluster_tag = f'<span class="news-cluster" style="color:#6B7280;font-size:11px">📊 클러스터 {cluster}건</span>'

    st.markdown(
        f'<div style="background:#FFFFFF;border:1px solid #E5E7EB;border-top:none;'
        f'border-radius:0 0 10px 10px;padding:12px 12px 8px;min-height:{min_h}px">'
        f'<div style="font-size:10.5px;color:#9CA3AF;margin-bottom:4px">'
        f'<strong style="color:#6B7280">{press}</strong>{(" · " + pub) if pub else ""}</div>'
        f'<div style="font-size:13px;font-weight:700;color:#111827;line-height:1.5;'
        f'margin-bottom:6px;display:-webkit-box;-webkit-line-clamp:3;'
        f'-webkit-box-orient:vertical;overflow:hidden">{title}</div>'
        f'<div style="font-size:12px;color:#6B7280;line-height:1.6;margin-bottom:6px;">{lede}</div>'
        f'{cluster_tag}'
        f'</div>',
        unsafe_allow_html=True,
    )

def _card_btns(article: dict, idx: int) -> None:
    url = article.get("article_meta", {}).get("url", "")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    _, b1, b2 = st.columns([2, 1, 1])
    with b1:
        if st.button("분석 보기", key=f"detail_{idx}", use_container_width=True, type="primary"):
            st.session_state.selected_article_for_detail = article
            st.switch_page("pages/4_News_Detail.py")
    with b2:
        if url:
            st.link_button("원문 →", url, use_container_width=True)

# ─ 2열 균일 카드 그리드 ─────────────────
for row_start in range(0, len(headlines), 2):
    row_items = headlines[row_start:row_start + 2]
    cols = st.columns(2)
    for col_idx, article in enumerate(row_items):
        idx = row_start + col_idx
        with cols[col_idx]:
            # 이미지 링크가 있다면 _card_img 추가 (통합 JSON 구조에 맞춰 조정)
            st.markdown(f'<div style="border-radius:10px 10px 0 0;height:160px;background:#F3F4F6;'
                        f'border:1px solid #E5E7EB;border-bottom:none;display:flex;align-items:center;'
                        f'justify-content:center;font-size:30px;opacity:.25">📰</div>', unsafe_allow_html=True)
            _card_body(article, min_h=120)
            _card_btns(article, idx)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)