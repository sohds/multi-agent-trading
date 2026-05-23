"""
뉴스 분석 상세 페이지
기사 원문(하이라이트) → 용어 해설 → 해당 기사 퀴즈를 모두 보여줍니다.
"""

import streamlit as st
import sys
import os
import html

DASHBOARD_DIR = os.path.dirname(os.path.dirname(__file__))
ROOT = os.path.dirname(DASHBOARD_DIR)

sys.path.insert(0, DASHBOARD_DIR)
sys.path.insert(0, os.path.join(ROOT, "news-translator"))
from utils.quiz_state import answer_quiz, get_quiz_state, reset_quiz
from utils.styles import inject_css, sec_title, callout
from news_helper.text_match import find_term

st.set_page_config(page_title="뉴스 분석 | AI 주식 브리핑", page_icon="📰", layout="wide")
inject_css()

st.markdown("""
<style>
/* 툴팁을 가진 하이라이트 단어 스타일 */
.hl-term {
    position: relative;
    cursor: help;
    padding: 0.1rem 0.3rem;
    border-radius: 4px;
    font-weight: 700;
    color: #111827;
    border-bottom: 1px dashed rgba(0,0,0,0.3);
    transition: filter 0.2s;
}
.hl-term:hover {
    filter: brightness(0.95);
}
/* 말풍선(Tooltip) 스타일 */
.hl-tooltip {
    visibility: hidden;
    width: max-content;
    max-width: 250px;
    background-color: #1F2937; /* 진한 회색 바탕 */
    color: #F9FAFB;
    text-align: left;
    border-radius: 6px;
    padding: 8px 12px;
    position: absolute;
    z-index: 9999;
    bottom: 130%; /* 단어 위쪽에 배치 */
    left: 50%;
    transform: translateX(-50%);
    font-size: 12px;
    font-weight: 400;
    line-height: 1.5;
    opacity: 0;
    transition: opacity 0.2s, bottom 0.2s;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    pointer-events: none; /* 마우스 간섭 방지 */
}
/* 말풍선 꼬리표(화살표) */
.hl-tooltip::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: -5px;
    border-width: 5px;
    border-style: solid;
    border-color: #1F2937 transparent transparent transparent;
}
/* 마우스를 올렸을 때 말풍선 나타나기 */
.hl-term:hover .hl-tooltip {
    visibility: visible;
    opacity: 1;
    bottom: 115%;
}
/* O/X 버튼: rounded-rect, ghost-orange */
[data-testid="stButton"] > button[kind="primary"] {
    background: #FFFFFF !important;
    color: #EA580C !important;
    border: 1px solid #FED7AA !important;
    border-radius: 10px !important;
    padding: 0.45rem 1.4rem !important;
    min-height: 38px !important;
    letter-spacing: 0.2px !important;
    transition: background 150ms ease, border-color 150ms ease, color 150ms ease !important;
}
[data-testid="stButton"] > button[kind="primary"],
[data-testid="stButton"] > button[kind="primary"] * {
    font-size: 14px !important;
    font-weight: 700 !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #FFF7ED !important;
    border-color: #F97316 !important;
    color: #C2410C !important;
    filter: none !important;
}
/* 뒤로가기·보조 버튼: rounded-rect, neutral */
[data-testid="stButton"] > button[kind="secondary"],
[data-testid="stButton"] > button[kind="secondary"] * {
    font-size: 13px !important;
    font-weight: 500 !important;
}
</style>
""", unsafe_allow_html=True)

# ── 뒤로가기 ─────────────────────────────────
if st.button("← 뉴스 목록으로"):
    st.switch_page("pages/2_News_Translator.py")

article = st.session_state.get("selected_article_for_detail")

if not article:
    callout("선택된 기사가 없습니다. 뉴스 번역기 페이지에서 기사를 선택해주세요.", kind="warn")
    st.stop()

# ── 1. 데이터 파싱 ──────────────────────────
meta = article.get("article_meta", {})
title = meta.get("title", "제목 없음")
press = meta.get("press", "언론사 미상")
pub = meta.get("published_at", "")
cluster = meta.get("cluster_num", 0)
url = meta.get("url", "")
image_url = meta.get("image_url") or ""

body_text = article.get("article_body", "본문이 없습니다.")
analysis = article.get("translated_terms", {})
quiz = article.get("quiz", {})
translation_error = article.get("translation_error")

difficult_terms = analysis.get("difficult_terms", []) if analysis else []

# ── 2. 본문 하이라이트 로직 (컬러맵 & 툴팁 & UUID 치환) ──────────────────────────────────────

def get_difficulty_color(score: float) -> str:
    """
    난이도 점수(0.5 ~ 1.0)에 따라 HSL 색상을 생성합니다.
    0.5 근처: 노란색 (Hue 60)
    0.75 근처: 주황색 (Hue 30)
    1.0 근처: 붉은색 (Hue 0)
    """
    # 안전하게 점수를 0.5 ~ 1.0 사이로 고정
    clamped_score = max(0.5, min(1.0, score))
    # 0.5~1.0을 0.0~1.0 비율로 변환
    ratio = (clamped_score - 0.5) / 0.5 
    # 색상 톤(Hue) 계산: 60(노랑)에서 0(빨강)으로 내려감
    hue = int(60 * (1 - ratio))
    # 채도 100%, 밝기 85%로 은은한 형광펜 효과
    return f"hsl({hue}, 100%, 85%)"

def _html_text(value: str) -> str:
    return html.escape(value).replace("\n", "<br><br>")


def _score_value(raw_score) -> float:
    try:
        return float(raw_score)
    except (TypeError, ValueError):
        return 0.5


def _highlight_html(surface: str, term_obj: dict) -> str:
    score = _score_value(term_obj.get("difficulty_score", 0.5))
    explanation = html.escape(str(term_obj.get("explanation") or "설명이 없습니다."))
    bg_color = get_difficulty_color(score)
    return (
        f'<span class="hl-term" style="background-color:{bg_color}">{html.escape(surface)}'
        f'<span class="hl-tooltip"><strong style="color:#FCA5A5">난이도: {score}</strong><br>{explanation}</span>'
        f'</span>'
    )


def _highlight_article_body(body: str, terms: list[dict]) -> str:
    candidates = [
        {**term, "term": str(term.get("term") or "").strip()}
        for term in terms
        if str(term.get("term") or "").strip()
    ]
    candidates.sort(key=lambda item: len(item["term"]), reverse=True)

    parts: list[str] = []
    index = 0
    while index < len(body):
        best_match = None
        for term_obj in candidates:
            word = term_obj["term"]
            match_index = find_term(body, word, index)
            if match_index == -1:
                continue
            match_key = (match_index, -len(word))
            if best_match is None or match_key < best_match[0]:
                best_match = (match_key, word, term_obj)

        if best_match is None:
            parts.append(_html_text(body[index:]))
            break

        (match_index, _), word, term_obj = best_match
        if match_index > index:
            parts.append(_html_text(body[index:match_index]))

        match_end = match_index + len(word)
        parts.append(_highlight_html(body[match_index:match_end], term_obj))
        index = match_end

    return "".join(parts)


highlighted_body = _highlight_article_body(body_text, difficult_terms)


# ── 3. 화면 렌더링 ──────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:1.5rem; margin-top:1rem;">
    <div style="font-size:24px;font-weight:900;color:#111827;line-height:1.45">{title}</div>
    <div style="font-size:13px;color:#6B7280;margin-top:10px;">
        <strong>{press}</strong> · {pub}
    </div>
</div>
""", unsafe_allow_html=True)

main_col, side_col = st.columns([3, 1])

with main_col:
    if image_url:
        safe_image_url = html.escape(image_url, quote=True)
        st.markdown(f"""
        <div style="border-radius:14px;overflow:hidden;height:340px;background:#F3F4F6;
                    border:1px solid #E5E7EB;margin-bottom:22px;display:flex;
                    align-items:center;justify-content:center">
            <img src="{safe_image_url}" referrerpolicy="no-referrer" crossorigin="anonymous"
                 style="width:100%;height:100%;object-fit:contain"
                 onerror="this.parentElement.style.display='none'">
        </div>
        """, unsafe_allow_html=True)

    if translation_error:
        callout(f"⚠️ {translation_error}", kind="warn")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-bottom:10px; font-size:13px; color:#6B7280;">
        💡 <b>Tip:</b> 색칠된 단어 위에 마우스를 올리면 뜻을 볼 수 있습니다. (붉은색일수록 어려운 단어)
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="font-size:15px;color:#374151;line-height:2.0;margin-bottom:30px; padding:24px; background:#FFFFFF; border-radius:12px; border:1px solid #E5E7EB; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
        {highlighted_body}
    </div>
    """, unsafe_allow_html=True)

    # --- [파트 B] 금융 용어 해설 모아보기 (선택 사항) ---
    with st.expander("📖 기사 속 금융 용어 전체 모아보기"):
        if difficult_terms:
            for term in difficult_terms:
                st.markdown(f"""
                <div style="margin-bottom:10px; padding:12px 16px; border-left:4px solid #7C3AED; background:#F5F3FF; border-radius:4px;">
                    <div style="font-weight:700; color:#4C1D95; font-size:14px; margin-bottom:4px;">{term.get('term')} <span style="font-size:12px; color:#9CA3AF; font-weight:500;">(점수: {term.get('difficulty_score', 0)})</span></div>
                    <div style="font-size:13px; color:#374151;">{term.get('explanation')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("추출된 금융 용어가 없습니다.")

    # --- [파트 C] OX 투자 퀴즈 ---
    if quiz:
        st.divider()
        sec_title("🧩 방금 읽은 기사, OX 퀴즈로 확인!")
        
        question = quiz.get("question", "")
        answer = quiz.get("answer", "")
        explanation = quiz.get("explanation", "")
        quiz_state = get_quiz_state(article)

        st.markdown(f"""
        <div style="padding:20px; border:2px solid #E5E7EB; border-radius:12px; margin-bottom:20px; background-color:#F9FAFB">
            <div style="font-size:16px; font-weight:700; color:#111827; margin-bottom:20px;">
                Q. {question}
            </div>
        """, unsafe_allow_html=True)

        if not quiz_state["answered"]:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⭕ 맞다 (O)", use_container_width=True, type="primary"):
                    answer_quiz(article, "O")
                    st.rerun()
            with col2:
                if st.button("❌ 틀리다 (X)", use_container_width=True, type="primary"):
                    answer_quiz(article, "X")
                    st.rerun()
        else:
            selected = quiz_state["selected"]
            is_correct = bool(quiz_state["is_correct"])

            if is_correct:
                st.success(f"🎉 정답입니다! (선택: {selected})")
            else:
                st.error(f"앗, 틀렸습니다! (정답: {answer} / 내 선택: {selected})")

            st.info(f"**해설:** {explanation}")
            
            if st.button("↻ 퀴즈 다시 풀기", key="reset_quiz"):
                reset_quiz(article)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

with side_col:
    sec_title("기사 메타 정보")
    for label, value in [("언론사", press), ("발행일", pub[:16] if pub else "—"), ("클러스터", f"{cluster}건")]:
        st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:10px; padding:12px 14px;margin-bottom:8px">
            <div style="font-size:10px;color:#9CA3AF;margin-bottom:4px">{label}</div>
            <div style="font-size:14px;font-weight:700;color:#111827">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    if url:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        st.link_button("네이버 기사 원문 보기 →", url, use_container_width=True)
        
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    difficulty_low_color = get_difficulty_color(0.5)
    difficulty_mid_color = get_difficulty_color(0.75)
    difficulty_high_color = get_difficulty_color(1.0)

    st.markdown(f"""
    <div style="font-size:13px; font-weight:700; color:#374151; margin-bottom:10px;">난이도 색상 안내</div>
    <div style="display:flex; align-items:stretch; gap:12px; font-size:12px; color:#6B7280;">
        <div style="position:relative; width:26px; height:124px; border-radius:6px;
                    background:linear-gradient(to top, {difficulty_low_color} 0%, {difficulty_mid_color} 50%, {difficulty_high_color} 100%);
                    border:1px solid #E5E7EB; box-shadow:inset 0 0 0 1px rgba(255,255,255,0.45);">
            <div style="position:absolute; left:100%; top:0; width:7px; border-top:1px solid #9CA3AF;"></div>
            <div style="position:absolute; left:100%; top:50%; width:7px; border-top:1px solid #9CA3AF;"></div>
            <div style="position:absolute; left:100%; bottom:0; width:7px; border-top:1px solid #9CA3AF;"></div>
        </div>
        <div style="height:124px; display:flex; flex-direction:column; justify-content:space-between; padding:0 0 1px 0;">
            <div><span style="font-weight:700; color:#374151;">고난도</span> <span style="color:#9CA3AF;">1.0</span></div>
            <div><span style="font-weight:700; color:#374151;">심화</span> <span style="color:#9CA3AF;">0.75</span></div>
            <div><span style="font-weight:700; color:#374151;">일반</span> <span style="color:#9CA3AF;">0.5</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
