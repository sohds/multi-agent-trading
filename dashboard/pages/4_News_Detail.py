"""
뉴스 분석 상세 페이지

2_News_Translator.py에서 기사를 선택하면 이 페이지로 이동합니다.
실제 분석은 news-translator/ 모듈 연결 후 활성화됩니다.
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.styles import inject_css, sec_title, callout, badge

st.set_page_config(page_title="뉴스 분석 | AI 주식 브리핑", page_icon="📰", layout="wide")
inject_css()

st.markdown("""
<style>
[data-testid="stButton"] > button[kind="secondary"],
[data-testid="stButton"] > button[kind="secondary"] * {
    font-size: 13px !important;
    font-weight: 500 !important;
}
</style>
""", unsafe_allow_html=True)


def analyze_article(article: dict) -> dict | None:
    """
    기사 분석 결과를 반환합니다.

    실제 연동 예시:
        from news_translator.news_helper.cli import translate
        return translate(url=article.get("url"), text=article.get("body"))

    반환 구조:
    {
        "summary": str,
        "translated": str,
        "terms": [{"term": str, "definition": str}],
    }
    """
    return None


# ── 뒤로가기 ─────────────────────────────────
if st.button("← 뉴스 목록으로"):
    st.switch_page("pages/2_News_Translator.py")

article = st.session_state.get("selected_article_for_detail")

if not article:
    callout(
        "선택된 기사가 없습니다. 뉴스 번역기 페이지에서 기사를 선택해주세요.",
        kind="warn",
    )
    st.stop()

# ── 기사 데이터 파싱 ──────────────────────────
title     = article.get("title", "제목 없음")
press     = article.get("press", "")
pub       = article.get("published_at", "")
pub_short = pub[:16] if pub else ""
lede      = article.get("lede", "")
image_url = article.get("image_url", "")
cluster   = article.get("cluster_num", 0)
url       = article.get("url", "")
body      = article.get("body", "")

# cluster 태그
if cluster and cluster > 50:
    cluster_html = f'<span style="color:#F97316;font-weight:600">🔥 클러스터 {cluster}건</span>'
elif cluster:
    cluster_html = f'<span style="color:#6B7280">📊 클러스터 {cluster}건</span>'
else:
    cluster_html = ""

# ── 페이지 헤더 ───────────────────────────────
st.markdown(f"""
<div style="margin-bottom:1.5rem">
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
    letter-spacing:1.2px;color:#7C3AED;margin-bottom:8px">News Analysis</div>
    <div style="font-size:22px;font-weight:900;color:#111827;line-height:1.45">{title}</div>
    <div style="font-size:13px;color:#6B7280;margin-top:10px;display:flex;
    align-items:center;gap:10px;flex-wrap:wrap">
        {"<strong style='color:#374151'>" + press + "</strong>" if press else ""}
        {"<span style='color:#D1D5DB'>·</span><span>" + pub_short + "</span>" if pub_short else ""}
        {"<span style='color:#D1D5DB'>·</span>" + cluster_html if cluster_html else ""}
    </div>
</div>
""", unsafe_allow_html=True)

# ── 메인 / 사이드 레이아웃 ────────────────────
main_col, side_col = st.columns([3, 1])

with main_col:
    # 이미지
    if image_url:
        st.markdown(f"""
        <div style="border-radius:14px;overflow:hidden;max-height:340px;
        background:#F3F4F6;margin-bottom:20px;border:1px solid #E5E7EB">
            <img src="{image_url}" referrerpolicy="no-referrer" crossorigin="anonymous"
                 style="width:100%;max-height:340px;object-fit:cover;display:block"
                 onerror="this.parentElement.style.display='none'">
        </div>
        """, unsafe_allow_html=True)

    # 리드 문장
    if lede:
        st.markdown(f"""
        <div style="background:#F5F3FF;border-left:3px solid #7C3AED;
        border-radius:0 10px 10px 0;padding:16px 20px;margin-bottom:20px;
        font-size:14px;color:#374151;line-height:1.85">
            {lede}
        </div>
        """, unsafe_allow_html=True)

    # 본문 (lede와 다를 경우만)
    if body and body.strip() != lede.strip():
        body_text = body[:1200] + "…" if len(body) > 1200 else body
        st.markdown(f"""
        <div style="font-size:14px;color:#374151;line-height:1.9;margin-bottom:20px">
            {body_text}
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── AI 분석 결과 ──────────────────────────
    sec_title("AI 뉴스 분석")

    analysis = analyze_article(article)

    if analysis:
        summary    = analysis.get("summary", "")
        translated = analysis.get("translated", "")
        terms      = analysis.get("terms", [])

        if summary:
            st.markdown(f"""
            <div class="translate-result">
                <div class="translate-result-title">📄 3줄 요약</div>
                <div class="translate-result-body">{summary}</div>
            </div>
            """, unsafe_allow_html=True)

        if translated:
            st.markdown(f"""
            <div class="translate-result" style="margin-top:8px">
                <div class="translate-result-title">💬 쉬운 말 번역</div>
                <div class="translate-result-body">{translated}</div>
            </div>
            """, unsafe_allow_html=True)

        if terms:
            sec_title("금융 용어 해설")
            for term in terms:
                st.markdown(
                    f'<div class="term-item">'
                    f'<div class="term-name">{term.get("term","—")}</div>'
                    f'<div class="term-def">{term.get("definition","—")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    else:
        callout(
            "🔄 번역·분석 기능은 <code>news-translator/</code> 모듈 연동 후 활성화됩니다.",
            kind="orange",
        )

        # 스켈레톤 플레이스홀더
        for label, width_list in [
            ("📄 3줄 요약", ["95%", "80%", "88%"]),
            ("💬 쉬운 말 번역", ["100%", "92%", "97%", "75%"]),
        ]:
            bars = "".join(
                f'<div style="background:#F3F4F6;height:14px;border-radius:4px;'
                f'width:{w};opacity:.45;margin-bottom:8px"></div>'
                for w in width_list
            )
            st.markdown(f"""
            <div class="translate-result" style="margin-top:8px">
                <div class="translate-result-title">{label}</div>
                {bars}
            </div>
            """, unsafe_allow_html=True)

        sec_title("금융 용어 해설")
        for term_txt, def_txt in [
            ("—", "LLM 연결 후 금융 용어가 표시됩니다"),
            ("—", "기사에서 추출된 핵심 용어를 쉽게 설명합니다"),
        ]:
            st.markdown(f"""
            <div class="term-item" style="opacity:.45">
                <div class="term-name">{term_txt}</div>
                <div class="term-def">{def_txt}</div>
            </div>
            """, unsafe_allow_html=True)

with side_col:
    sec_title("기사 정보")

    for label, value in [
        ("언론사", press or "—"),
        ("발행일", pub_short or "—"),
        ("클러스터", f"{cluster}건" if cluster else "—"),
    ]:
        st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:10px;
        padding:12px 14px;margin-bottom:8px">
            <div style="font-size:10px;color:#9CA3AF;margin-bottom:4px">{label}</div>
            <div style="font-size:14px;font-weight:700;color:#111827">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    if url:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        st.markdown(
            f'<a href="{url}" target="_blank" class="btn btn-ghost-purple"'
            f' style="width:100%;justify-content:center">'
            f'원문 바로가기 <span class="btn-arr">→</span></a>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    sec_title("다른 서비스")

    st.markdown("""
    <div style="font-size:12px;color:#6B7280;line-height:2.1">
        <div>💬 <strong style="color:#374151">토론 브리핑</strong></div>
        <div style="padding-left:12px;color:#9CA3AF;font-size:11px">관련 Bull/Bear 토론 보기</div>
        <div style="margin-top:6px">🧩 <strong style="color:#374151">투자 퀴즈</strong></div>
        <div style="padding-left:12px;color:#9CA3AF;font-size:11px">뉴스 기반 퀴즈 풀기</div>
    </div>
    """, unsafe_allow_html=True)
