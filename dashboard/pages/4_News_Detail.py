"""
뉴스 분석 상세 페이지
기사 원문(하이라이트) → 용어 해설 → 해당 기사 퀴즈를 모두 보여줍니다.
"""

import streamlit as st
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.styles import inject_css, sec_title, callout

st.set_page_config(page_title="뉴스 분석 | AI 주식 브리핑", page_icon="📰", layout="wide")
inject_css()

# ✨ 툴팁 및 커스텀 스타일 CSS
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

body_text = article.get("article_body", "본문이 없습니다.")
analysis = article.get("translated_terms", {})
quiz = article.get("quiz", {})

difficult_terms = analysis.get("difficult_terms", []) if analysis else []

# ── ✨ 2. 본문 하이라이트 로직 (컬러맵 & 툴팁 & UUID 치환) ──────────────────────────────────────

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

# 긴 단어부터 먼저 치환되도록 정렬 (예: '가처분'이 '가처분 신청' 안에서 치환되는 버그 방지)
difficult_terms_sorted = sorted(difficult_terms, key=lambda x: len(x.get("term", "")), reverse=True)

highlighted_body = body_text
replacements = {} # HTML 태그 깨짐을 방지하기 위한 UUID 저장소

# 1단계: 실제 단어들을 유니크한 UUID로 변경
for term_obj in difficult_terms_sorted:
    word = term_obj.get("term", "")
    if not word:
        continue
        
    score = term_obj.get("difficulty_score", 0.5)
    explanation = term_obj.get("explanation", "설명이 없습니다.")
    
    # 난이도에 따른 동적 배경색 가져오기
    bg_color = get_difficulty_color(score)
    
    # 툴팁이 포함된 HTML 구성
    uid = f"__UUID_{uuid.uuid4().hex}__"
    hl_html = (
        f'<span class="hl-term" style="background-color:{bg_color}">{word}'
        f'<span class="hl-tooltip"><strong style="color:#FCA5A5">난이도: {score}</strong><br>{explanation}</span>'
        f'</span>'
    )
    
    replacements[uid] = hl_html
    highlighted_body = highlighted_body.replace(word, uid)

# 2단계: UUID를 만들어둔 HTML 태그로 일괄 변경
for uid, html in replacements.items():
    highlighted_body = highlighted_body.replace(uid, html)

# 줄바꿈 태그 변환
highlighted_body = highlighted_body.replace("\n", "<br><br>")


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
    # --- [파트 A] 하이라이트된 기사 본문 ---
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

        quiz_key = f"quiz_answered_{url}"
        if quiz_key not in st.session_state:
            st.session_state[quiz_key] = False
            st.session_state[f"quiz_selected_{url}"] = None

        st.markdown(f"""
        <div style="padding:20px; border:2px solid #E5E7EB; border-radius:12px; margin-bottom:20px; background-color:#F9FAFB">
            <div style="font-size:16px; font-weight:700; color:#111827; margin-bottom:20px;">
                Q. {question}
            </div>
        """, unsafe_allow_html=True)

        if not st.session_state[quiz_key]:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⭕ 맞다 (O)", use_container_width=True, type="primary"):
                    st.session_state[quiz_key] = True
                    st.session_state[f"quiz_selected_{url}"] = "O"
                    st.rerun()
            with col2:
                if st.button("❌ 틀리다 (X)", use_container_width=True, type="primary"):
                    st.session_state[quiz_key] = True
                    st.session_state[f"quiz_selected_{url}"] = "X"
                    st.rerun()
        else:
            selected = st.session_state[f"quiz_selected_{url}"]
            is_correct = (selected == answer)

            if is_correct:
                st.success(f"🎉 정답입니다! (선택: {selected})")
            else:
                st.error(f"앗, 틀렸습니다! (정답: {answer} / 내 선택: {selected})")

            st.info(f"**해설:** {explanation}")
            
            if st.button("↻ 퀴즈 다시 풀기", key="reset_quiz"):
                st.session_state[quiz_key] = False
                st.session_state[f"quiz_selected_{url}"] = None
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
    
    # 컬러맵 범례 표시
    st.markdown("""
    <div style="font-size:13px; font-weight:700; color:#374151; margin-bottom:10px;">난이도 색상 안내</div>
    <div style="display:flex; flex-direction:column; gap:6px; font-size:12px; color:#6B7280;">
        <div style="display:flex; align-items:center; gap:8px;">
            <div style="width:14px; height:14px; border-radius:3px; background-color:hsl(60, 100%, 85%); border:1px solid #E5E7EB;"></div> 일반 (0.5)
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
            <div style="width:14px; height:14px; border-radius:3px; background-color:hsl(30, 100%, 85%); border:1px solid #E5E7EB;"></div> 심화 (0.75)
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
            <div style="width:14px; height:14px; border-radius:3px; background-color:hsl(0, 100%, 85%); border:1px solid #E5E7EB;"></div> 고난도 (1.0)
        </div>
    </div>
    """, unsafe_allow_html=True)