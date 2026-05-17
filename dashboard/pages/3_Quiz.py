"""
투자 퀴즈 — 서비스 페이지

당일 뉴스 기반 OX 퀴즈를 표시합니다.
실제 퀴즈는 load_quiz()에서 quiz_engine.py 결과를 불러오면 됩니다.
"""

import streamlit as st
import sys
import os
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


# ── 데이터 로드 (모듈 연결 시 교체) ───────────

def load_quiz() -> dict | None:
    """
    news-quiz/ 모듈의 quiz_engine.py 결과를 반환합니다.

    실제 연동 예시:
        import sys; sys.path.insert(0, "../")
        from news_quiz.quiz_engine import generate_quiz
        return generate_quiz()

    반환 구조:
    {
        "question": str,
        "options": ["O", "X"],
        "answer": str,
        "explanation": str,
        "difficulty": "쉬움" | "보통" | "어려움",
        "category": str,
        "news_reference": {"title": str, "url": str},
        "generated_at": str,
    }
    """
    return None


# ─────────────────────────────────────────────
now = datetime.now()

# Session state
if "quiz_data"     not in st.session_state:
    st.session_state.quiz_data     = load_quiz()
if "quiz_answered" not in st.session_state:
    st.session_state.quiz_answered = False
if "quiz_selected" not in st.session_state:
    st.session_state.quiz_selected = None

# ── 헤더 ──────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:1.5rem">
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
    letter-spacing:1.2px;color:#10B981;margin-bottom:6px">Daily Quiz</div>
    <div style="font-size:28px;font-weight:900;color:#111827">투자 퀴즈</div>
    <div style="font-size:14px;color:#6B7280;margin-top:6px">
        오늘의 경제 뉴스로 금융 지식을 테스트하세요. 정답 해설로 오늘의 이슈를 더 깊이 이해할 수 있습니다.
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="status-strip">
    <div><span class="dot dot-orange"></span>
    <span class="status-v live">{now.strftime('%Y년 %m월 %d일')} 퀴즈</span></div>
    <span class="sep">|</span>
    <div><span class="status-k">난이도 &nbsp;</span>
    <span class="status-v">{st.session_state.quiz_data.get('difficulty','—') if st.session_state.quiz_data else '—'}</span></div>
    <span class="sep">|</span>
    <div><span class="status-k">상태 &nbsp;</span>
    <span class="status-v">{'✅ 풀이 완료' if st.session_state.quiz_answered else '대기 중'}</span></div>
</div>
""", unsafe_allow_html=True)

# ── 퀴즈 생성 버튼 ────────────────────────────
gen_col, info_col = st.columns([1, 4])
with gen_col:
    if st.button("🎲 퀴즈 생성", use_container_width=True, type="primary"):
        st.session_state.quiz_data     = load_quiz()
        st.session_state.quiz_answered = False
        st.session_state.quiz_selected = None
        st.rerun()
with info_col:
    callout("퀴즈 생성 버튼은 <code>news-quiz/quiz_engine.py</code> 연결 후 실제 문제가 생성됩니다.", kind="orange")

st.divider()

# ── 메인 레이아웃 ─────────────────────────────
quiz = st.session_state.quiz_data
main_col, side_col = st.columns([3, 1])

with main_col:
    if quiz:
        question    = quiz.get("question", "—")
        options     = quiz.get("options", ["O", "X"])
        answer      = quiz.get("answer", "")
        explanation = quiz.get("explanation", "—")
        difficulty  = quiz.get("difficulty", "—")
        category    = quiz.get("category", "—")
        news_ref    = quiz.get("news_reference", {})
        gen_at      = quiz.get("generated_at", "")

        diff_badge = {"쉬움": "ok", "보통": "wip", "어려움": "off"}.get(difficulty, "off")

        # 퀴즈 카드
        st.markdown(f"""
        <div class="quiz-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                <div class="quiz-card-label">📝 오늘의 투자 퀴즈</div>
                <div style="display:flex;gap:6px">
                    {badge(difficulty, diff_badge)}
                    {badge(category, "off")}
                </div>
            </div>
            <div class="quiz-card-q">{question}</div>
            {"<div style='font-size:11px;color:#9CA3AF;margin-top:10px'>생성: " + gen_at[:16] + "</div>" if gen_at else ""}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        # 선택지
        if not st.session_state.quiz_answered:
            opt_cols = st.columns(len(options))
            for i, opt in enumerate(options):
                with opt_cols[i]:
                    opt_label = f"⭕ {opt}" if opt == "O" else (f"❌ {opt}" if opt == "X" else opt)
                    if st.button(opt_label, key=f"q_opt_{i}", use_container_width=True,
                                 type="primary" if opt in ["O", "X"] else "secondary"):
                        st.session_state.quiz_selected = opt
                        st.session_state.quiz_answered = True
                        st.rerun()
        else:
            selected  = st.session_state.quiz_selected
            is_correct = selected == answer

            # 결과
            if is_correct:
                st.success(f"✅ 정답입니다!  선택: **{selected}**")
                st.balloons()
            else:
                st.error(f"❌ 틀렸습니다.  선택: **{selected}**  /  정답: **{answer}**")

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
            if news_ref.get("title"):
                st.markdown(f"""
                <div style="margin-top:12px;padding:12px 16px;background:#FFFFFF;
                border:1px solid #E5E7EB;border-radius:10px;font-size:12.5px">
                    <span style="color:#9CA3AF">관련 뉴스: </span>
                    <strong style="color:#374151">{news_ref['title']}</strong>
                </div>
                """, unsafe_allow_html=True)
                if news_ref.get("url"):
                    st.link_button("원문 읽기 →", news_ref["url"])

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("🔄 다시 풀기", key="retry"):
                st.session_state.quiz_answered = False
                st.session_state.quiz_selected = None
                st.rerun()

    else:
        # Placeholder
        st.markdown(f"""
        <div class="quiz-card" style="text-align:center;min-height:200px;
        display:flex;flex-direction:column;align-items:center;justify-content:center">
            <div style="font-size:40px;margin-bottom:14px;opacity:.35">🧩</div>
            <div class="quiz-card-label">오늘의 투자 퀴즈</div>
            <div style="font-size:16px;font-weight:600;color:#374151;margin:10px 0;line-height:1.6">
                {now.strftime('%m월 %d일')} 퀴즈를 준비 중입니다
            </div>
            <div style="font-size:13px;color:#9CA3AF">
                위의 퀴즈 생성 버튼을 클릭하거나<br>
                quiz_engine.py 모듈을 연결하세요
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        # Dummy 버튼
        d1, d2 = st.columns(2)
        with d1:
            st.button("⭕  O", use_container_width=True, disabled=True)
        with d2:
            st.button("❌  X", use_container_width=True, disabled=True)

# ── 사이드 패널 ───────────────────────────────
with side_col:
    sec_title("학습 통계")

    st.markdown("""
    <div style="display:flex;flex-direction:column;gap:10px">
    """, unsafe_allow_html=True)

    stats = [
        ("오늘 풀기",  "—", "#F97316"),
        ("정답률",     "—", "#10B981"),
        ("연속 정답",  "—", "#7C3AED"),
        ("총 누적",    "—", "#6B7280"),
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
    callout("학습 통계는 예측 이력 DB 연동 후 활성화됩니다.", kind="orange")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    sec_title("어떻게 만드나요?")
    st.markdown("""
    <div style="font-size:12px;color:#6B7280;line-height:1.9">
        <div>1️⃣ 오늘 뉴스 수집</div>
        <div style="padding-left:14px;color:#9CA3AF">naver_headline_crawler.py</div>
        <div>2️⃣ LLM으로 퀴즈 생성</div>
        <div style="padding-left:14px;color:#9CA3AF">quiz_engine.py</div>
        <div>3️⃣ 정답 & 해설 포함</div>
        <div style="padding-left:14px;color:#9CA3AF">금융 리터러시 학습 유도</div>
    </div>
    """, unsafe_allow_html=True)
