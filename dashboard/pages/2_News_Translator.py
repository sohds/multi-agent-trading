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
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
NEWS_OUTPUT_DIR = os.path.join(ROOT, "output", "news")

# ── 최신 통합 데이터 로드 ───────────────────────────────
def load_latest_integrated_news() -> tuple[list[dict], str]:
    """가장 최근에 생성된 통합 데이터를 읽어오고 수집 시각을 반환합니다."""
    if not os.path.exists(NEWS_OUTPUT_DIR):
        return [], "—"
    
    files = glob.glob(os.path.join(NEWS_OUTPUT_DIR, "integrated_news_*.json"))
    if not files:
        return [], "—"
    
    latest_file = max(files, key=os.path.getctime)
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 파일 데이터 구조 내부나 파일 이름 등에서 수집 시각 추출
            # 여기서는 파일 구조에 담긴 crawled_at 혹은 첫 기사의 시간 활용
            crawled_at = "—"
            if data and isinstance(data, list):
                # 첫 기사에 분석된 시각 정보가 있다면 가져오기
                crawled_at = data[0].get("article_meta", {}).get("published_at", "—")[:16]
            return data, crawled_at
    except Exception:
        return [], "—"

# 데이터 로드
headlines, crawled_at = load_latest_integrated_news()

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

if headlines:
    engine_status = '<span style="color:#10B981; font-weight:700;">LLM (연결 완료)</span>'
    live_badge = f'뉴스 {len(headlines)}건 준비됨'
else:
    engine_status = '<span style="color:#9CA3AF; font-weight:500;">LLM (연결 대기)</span>'
    live_badge = '뉴스 0건 준비됨'

st.markdown(f"""
<div class="status-strip">
    <div><span class="dot dot-orange"></span>
    <span class="status-v live">{live_badge}</span></div>
    <span class="sep">|</span>
    <div><span class="status-k">수집 시각 &nbsp;</span><span class="status-v">{crawled_at}</span></div>
    <span class="sep">|</span>
    <div><span class="status-k">번역 엔진 &nbsp;</span><span class="status-v">{engine_status}</span></div>
</div>
""", unsafe_allow_html=True)

if not headlines:
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    callout("📭 수집된 뉴스가 없습니다. 백엔드 파이프라인(news_run_pipeline.py)을 먼저 실행해주세요.", kind="warn")
    st.stop()

# ── 뉴스 카드 그리드 ──────────────────────────
sec_title(f"오늘의 핵심 경제 뉴스 ({len(headlines)}건)")

def _card_body(article: dict, min_h: int) -> None:
    meta = article.get("article_meta", {})
    title   = meta.get("title", "제목 없음")
    press   = meta.get("press", "")
    pub     = (meta.get("published_at") or "")[:10]
    cluster = meta.get("cluster_num", 0)
    
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

# ── 뉴스 카드 썸네일 이미지 함수 ──────────────────────
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

# ─ 2열 균일 카드 그리드 출력 로직 ─────────────────
for row_start in range(0, len(headlines), 2):
    row_items = headlines[row_start:row_start + 2]
    cols = st.columns(2)
    for col_idx, article in enumerate(row_items):
        idx = row_start + col_idx
        with cols[col_idx]:
            img_url = article.get("article_meta", {}).get("image_url", "")
            _card_img(img_url, height=160)
            
            _card_body(article, min_h=120)
            _card_btns(article, idx)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

st.divider()

if headlines:
    callout(
        "🎉 <b>다중 에이전트 연동 완료:</b> 현재 화면의 모든 뉴스는 실시간 LLM 번역 및 투자 퀴즈가 포함된 통합 데이터입니다.",
        kind="success",  
    )
else:
    callout(
        "🔄 번역 기능은 <code>news-translator/</code> 및 통합 파이프라인 연동 후 활성화됩니다. 백엔드를 실행해 주세요.",
        kind="orange", 
    )