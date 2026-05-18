"""
투자 퀴즈 — 서비스 페이지
통합 파이프라인에서 생성된 최신 JSON 데이터를 불러와 퀴즈만 모아서 제공합니다.
"""

import streamlit as st
import sys
import os
import json
import glob
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.styles import inject_css, badge, sec_title, callout

st.set_page_config(page_title="투자 퀴즈 | AI 주식 브리핑", page_icon="🧩", layout="wide")
inject_css()

st.markdown("""
<style>
[data-testid="stButton"] > button[kind="primary"] {
    background: #FFFFFF !important;
    color: #EA580C !important;
    border: 1px solid #FED7AA !important;
    border-radius: 7px !important;
    font-weight: 500 !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #FFF7ED !important;
    border-color: #F97316 !important;
    color: #C2410C !important;
    filter: none !important;
}
</style>
""", unsafe_allow_html=True)

# ── 경로 및 데이터 로드 ───────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
NEWS_OUTPUT_DIR = os.path.join(ROOT, "output", "news")

def load_latest_quizzes() -> list[dict]:
    """가장 최신 통합 JSON에서 퀴즈가 있는 기사만 추출"""
    if not os.path.exists(NEWS_OUTPUT_DIR):
        return []
    
    files = glob.glob(os.path.join(NEWS_OUTPUT_DIR, "integrated_news_*.json"))
    if not files:
        return []
    
    latest_file = max(files, key=os.path.getctime)
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 퀴즈 데이터가 존재하는 기사만 필터링
            return [item for item in data if item.get("quiz")]
    except Exception:
        return []

# ─────────────────────────────────────────────
now = datetime.now()
quiz_articles = load_latest_quizzes()

# ── 헤더 ──────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:1.5rem">
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
    letter-spacing:1.2px;color:#10B981;margin-bottom:6px">Daily Quiz</div>
    <div style="font-size:28px;font-weight:900;color:#111827">투자 퀴즈 모아보기</div>
    <div style="font-size:14px;color:#6B7280;margin-top:6px">
        오늘의 경제 뉴스로 금융 지식을 테스트하세요. 정답 해설로 이슈를 더 깊이 이해할 수 있습니다.
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="status-strip">
    <div><span class="dot dot-orange"></span>
    <span class="status-v live">{now.strftime('%Y년 %m월 %d일')} 퀴즈</span></div>
    <span class="sep">|</span>
    <div><span class="status-k">준비된 퀴즈 &nbsp;</span>
    <span class="status-v">{len(quiz_articles)}개</span></div>
</div>
""", unsafe_allow_html=True)
st.divider()

if not quiz_articles:
    callout("📭 수집된 퀴즈가 없습니다. 뉴스 번역기 파이프라인을 먼저 실행해주세요.", kind="warn")
    st.stop()

# ── 메인 레이아웃 ─────────────────────────────
main_col, side_col = st.columns([3, 1])

with main_col:
    # 퀴즈 선택 드롭다운
    st.markdown("<div style='font-size:14px; font-weight:700; color:#374151; margin-bottom:8px'>풀어볼 퀴즈를 선택하세요:</div>", unsafe_allow_html=True)
    
    # Selectbox를 위해 기사 제목 리스트 생성
    titles = [item.get("article_meta", {}).get("title", f"퀴즈 {i+1}") for i, item in enumerate(quiz_articles)]
    selected_title = st.selectbox("기사 선택", options=titles, label_visibility="collapsed")
    
    # 선택된 기사 찾기
    selected_idx = titles.index(selected_title)
    article = quiz_articles[selected_idx]
    
    quiz = article.get("quiz", {})
    meta = article.get("article_meta", {})
    
    question    = quiz.get("question", "—")
    answer      = quiz.get("answer", "")
    explanation = quiz.get("explanation", "—")
    
    # Session state 초기화 (문제가 바뀔 때마다 풀이 상태 초기화)
    quiz_key = f"quiz_standalone_{selected_idx}"
    if f"{quiz_key}_answered" not in st.session_state:
        st.session_state[f"{quiz_key}_answered"] = False
        st.session_state[f"{quiz_key}_selected"] = None

    # 퀴즈 카드
    st.markdown(f"""
    <div class="quiz-card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
            <div class="quiz-card-label">📝 오늘의 투자 퀴즈</div>
            <div style="display:flex;gap:6px">
                {badge("경제/금융", "off")}
            </div>
        </div>
        <div class="quiz-card-q">{question}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # 선택지 로직
    if not st.session_state[f"{quiz_key}_answered"]:
        opt_cols = st.columns(2)
        with opt_cols[0]:
            if st.button("⭕ 맞다 (O)", key=f"btn_O_{selected_idx}", use_container_width=True, type="primary"):
                st.session_state[f"{quiz_key}_answered"] = True
                st.session_state[f"{quiz_key}_selected"] = "O"
                st.rerun()
        with opt_cols[1]:
            if st.button("❌ 틀리다 (X)", key=f"btn_X_{selected_idx}", use_container_width=True, type="primary"):
                st.session_state[f"{quiz_key}_answered"] = True
                st.session_state[f"{quiz_key}_selected"] = "X"
                st.rerun()
    else:
        selected  = st.session_state[f"{quiz_key}_selected"]
        is_correct = (selected == answer)

        # 결과
        if is_correct:
            st.success(f"✅ 정답입니다!  선택: **{selected}**")
            st.balloons()
        else:
            st.error(f"❌ 틀렸습니다.  선택: **{selected}** /  정답: **{answer}**")

        # 해설 카드
        st.markdown(f"""
        <div style="background:{'#ECFDF5' if is_correct else '#FEF2F2'};
        border:1.5px solid {'#A7F3D0' if is_correct else '#FECACA'};
        border-radius:12px;padding:20px;margin-top:14px">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;
            letter-spacing:.8px;color:{'#059669' if is_correct else '#DC2626'};margin-bottom:8px">
                {'✅ 정답 해설' if is_correct else '📖 해설'}
            </div>
            <div style="font-size:14px;color:#111827;line-height:1.8">{explanation}</div>
        </div>
        """, unsafe_allow_html=True)

        # 관련 뉴스
        if meta.get("title"):
            st.markdown(f"""
            <div style="margin-top:12px;padding:12px 16px;background:#FFFFFF;
            border:1px solid #E5E7EB;border-radius:10px;font-size:12.5px">
                <span style="color:#9CA3AF">출제 배경 기사: </span>
                <strong style="color:#374151">{meta['title']}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                # 기사 상세 분석 페이지로 넘어가기
                if st.button("🔍 상세 분석 보기", key=f"detail_{selected_idx}", use_container_width=True):
                    st.session_state.selected_article_for_detail = article
                    st.switch_page("pages/4_News_Detail.py")
            with col_btn2:
                if meta.get("url"):
                    st.link_button("📰 기사 원문 읽기 →", meta["url"], use_container_width=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("🔄 다시 풀기", key=f"retry_{selected_idx}"):
            st.session_state[f"{quiz_key}_answered"] = False
            st.session_state[f"{quiz_key}_selected"] = None
            st.rerun()

# ── 사이드 패널 ───────────────────────────────
with side_col:
    sec_title("학습 통계")

    st.markdown("""
    <div style="display:flex;flex-direction:column;gap:10px">
    """, unsafe_allow_html=True)

    stats = [
        ("오늘 퀴즈 수", f"{len(quiz_articles)}개", "#F97316"),
        ("정답률", "—", "#10B981"),
        ("연속 정답", "—", "#7C3AED"),
    ]
    for label, value, color in stats:
        st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:10px;
        padding:14px 16px;border-left:3px solid {color}">
            <div style="font-size:11px;color:#9CA3AF;margin-bottom:4px">{label}</div>
            <div style="font-size:22px;font-weight:800;color:#111827">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    callout("정답률 통계는 데이터베이스 연동 후 활성화됩니다.", kind="orange")

