"""
AI 주식 브리핑 대시보드 — 서비스 랜딩 페이지

실행: streamlit run dashboard/app.py
"""

import streamlit as st
from datetime import datetime
import json
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(__file__))
from utils.styles import inject_css, badge, sec_title

st.set_page_config(
    page_title="AI 주식 브리핑",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ── 경로 상수 ─────────────────
ROOT           = os.path.dirname(os.path.dirname(__file__))
SESSION_JSON   = os.path.join(ROOT, "config", "session.json")
NEWS_OUTPUT_DIR = os.path.join(ROOT, "output", "news")

# ── 데이터 로드 헬퍼 ──────────────────────────
def load_session() -> dict | None:
    if os.path.exists(SESSION_JSON):
        try:
            return json.load(open(SESSION_JSON, encoding="utf-8"))
        except Exception:
            return None
    return None


def load_latest_integrated_news() -> list[dict]:
    if not os.path.exists(NEWS_OUTPUT_DIR):
        return []
    files = glob.glob(os.path.join(NEWS_OUTPUT_DIR, "*.json"))
    if not files:
        return []
    latest_file = max(files, key=os.path.getctime)
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

# 실시간 통합 뉴스 데이터 로드
integrated_news = load_latest_integrated_news()
headline_cnt = len(integrated_news)


def load_headline_preview(data_list: list, n: int = 3) -> list[tuple[str, str]]:
    """뉴스 번역기 미리보기용: 통합 데이터에서 (title, press) 튜플 최대 n개 반환"""
    previews = []
    for item in data_list[:n]:
        meta = item.get("article_meta", {})
        title = meta.get("title", "")[:48]
        press = meta.get("press", "")
        if title:
            previews.append((title, press))
    return previews


@st.cache_data(ttl=300)
def load_market_indices() -> list[dict]:
    """yfinance로 주요 지수·환율·원자재 현재가와 5일 추이를 반환합니다."""
    TICKERS = [
        ("^KS11",  "KOSPI",    "국내지수"),
        ("^KQ11",  "KOSDAQ",   "국내지수"),
        ("^GSPC",  "S&P 500",  "해외지수"),
        ("^IXIC",  "나스닥",   "해외지수"),
        ("^N225",  "닛케이",   "해외지수"),
        ("KRW=X",  "달러/원",  "환율/원자재"),
        ("GC=F",   "금",       "환율/원자재"),
        ("CL=F",   "WTI유",    "환율/원자재"),
    ]
    try:
        import yfinance as yf
        result = []
        for sym, name, cat in TICKERS:
            try:
                hist = yf.Ticker(sym).history(period="5d")
                if hist.empty:
                    continue
                closes = hist["Close"].dropna().tolist()
                if not closes:
                    continue
                close = float(closes[-1])
                prev  = float(closes[-2]) if len(closes) >= 2 else close
                change = close - prev
                change_pct = (change / prev * 100) if prev else 0.0
                result.append({
                    "sym": sym, "name": name, "category": cat,
                    "close": close, "change": change,
                    "change_pct": change_pct,
                    "history": [float(v) for v in closes],
                })
            except Exception:
                continue
        return result
    except Exception:
        return []


def _svg_sparkline(values: list[float], positive: bool, width: int = 80, height: int = 36) -> str:
    if not values or len(values) < 2:
        return ""
    mn, mx = min(values), max(values)
    if mx == mn:
        mn -= 1; mx += 1
    color      = "#EF4444" if positive else "#1D4ED8"
    fill_color = "rgba(239,68,68,0.12)" if positive else "rgba(29,78,216,0.12)"
    pad = 2
    pts = [
        (pad + (i / (len(values) - 1)) * (width - 2 * pad),
         (height - pad) - ((v - mn) / (mx - mn)) * (height - 2 * pad))
        for i, v in enumerate(values)
    ]
    line_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area_d   = f"M {pts[0][0]:.1f},{pts[0][1]:.1f}"
    for x, y in pts[1:]:
        area_d += f" L {x:.1f},{y:.1f}"
    area_d += f" L {pts[-1][0]:.1f},{height} L {pts[0][0]:.1f},{height} Z"
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block">'
        f'<path d="{area_d}" fill="{fill_color}"/>'
        f'<polyline points="{line_pts}" fill="none" stroke="{color}" '
        f'stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>'
        f'</svg>'
    )


# ── Sidebar ───────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-top">
        <span class="sidebar-logo">📊</span>
        <div class="sidebar-name">AI 주식 브리핑</div>
        <div class="sidebar-tagline">멀티에이전트 투자 분석 서비스</div>
    </div>
    """, unsafe_allow_html=True)

    now = datetime.now()
    st.markdown(f"""
    <div style="padding:8px 4px 12px;font-size:12px;color:#9CA3AF;line-height:2">
        <div>📅 &nbsp;{now.strftime('%Y년 %m월 %d일 (%a)')}</div>
        <div>🕐 &nbsp;{now.strftime('%H:%M')} KST</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("""
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
    letter-spacing:1px;color:#9CA3AF;margin-bottom:8px">서비스 Status</div>
    """, unsafe_allow_html=True)

    session       = load_session()
    debate_status = "구동 중" if session else "대기 중"
    debate_kind   = "ok" if session else "off"
    
    # 자동 감지 상태 갱신
    news_status   = f"뉴스 {headline_cnt}건" if headline_cnt else "대기 중"
    news_kind     = "ok" if headline_cnt else "off"
    quiz_status   = "준비됨" if headline_cnt else "대기 중"
    quiz_kind     = "ok" if headline_cnt else "off"

    for icon, name, status, kind in [
        ("💬", "토론 브리핑", debate_status, debate_kind),
        ("📰", "뉴스 번역기", news_status,   news_kind),
        ("🧩", "투자 퀴즈",   quiz_status,   quiz_kind),
    ]:
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:8px 0;border-bottom:1px solid #F3F4F6">'
            f'<div style="font-size:13px;color:#374151">{icon} &nbsp;{name}</div>'
            f'{badge(status, kind)}'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    st.markdown("""
    <div style="font-size:11px;color:#9CA3AF;line-height:1.9">
        <div>🤖 LLM: GPT-5.4 mini</div>
        <div>📡 데이터: yfinance · DART · PyKRX · 네이버</div>
        <div>🧠 패턴: Bull/Bear 토론 에이전트</div>
    </div>
    """, unsafe_allow_html=True)


# ── Hero ──────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-label">BITAmin 1학기 프로젝트</div>
    <div class="hero-title">AI 주식 브리핑 시스템</div>
    <div class="hero-sub">
        멀티에이전트가 오늘의 뉴스를 분석하고 토론합니다.<br>
        불(Bull) · 베어(Bear) 에이전트의 데이터 기반 토론과 최종 판정을 확인하세요.
    </div>
</div>
""", unsafe_allow_html=True)

# ── Status strip ─────────────────────────────
debate_topic_short = "—"
if session and session.get("stock_debate"):
    t = session["stock_debate"].get("debate_topic", "")
    debate_topic_short = t[:40] + "..." if len(t) > 40 else t

st.markdown(f"""
<div class="status-strip">
    <div><span class="dot dot-orange"></span><span class="status-v live">서비스 가동 중</span></div>
    <span class="sep">|</span>
    <div><span class="status-k">오늘 날짜 &nbsp;</span><span class="status-v">{now.strftime('%Y.%m.%d')}</span></div>
    <span class="sep">|</span>
    <div><span class="status-k">오늘의 주제 &nbsp;</span><span class="status-v">{debate_topic_short}</span></div>
    <span class="sep">|</span>
    <div><span class="status-k">준비된 뉴스 &nbsp;</span><span class="status-v">{headline_cnt}건</span></div>
</div>
""", unsafe_allow_html=True)

# ── 시장 현황 ──────────────────────────────────
market_data = load_market_indices()
if market_data:
    sec_title("시장 현황")

    CAT_LABELS = {
        "국내지수":    "국내 지수",
        "해외지수":    "해외 지수",
        "환율/원자재": "환율 · 원자재",
    }
    CAT_ORDER = ["국내지수", "해외지수", "환율/원자재"]

    groups: dict = {}
    for item in market_data:
        groups.setdefault(item["category"], []).append(item)

    filled_cats = [c for c in CAT_ORDER if groups.get(c)]
    rows_html = ""
    for cat in filled_cats:
        items = groups.get(cat, [])
        label = CAT_LABELS.get(cat, cat)
        is_last = (cat == filled_cats[-1])
        items_html = ""
        for i, item in enumerate(items):
            up      = item["change"] >= 0
            clr     = "#EF4444" if up else "#1D4ED8"
            bg_pill = "#FEE2E2" if up else "#DBEAFE"
            arr     = "▲" if up else "▼"
            sgn     = "+" if up else ""
            close_s = f"{item['close']:,.2f}"
            pct_s   = f"{sgn}{item['change_pct']:.2f}%"
            spark   = _svg_sparkline(item["history"], up, width=52, height=20)
            sep     = '<div style="width:1px;background:#E5E7EB;align-self:stretch;margin:0 10px"></div>' if i > 0 else ""
            items_html += (
                f'{sep}'
                f'<div style="display:inline-flex;align-items:center;gap:7px;white-space:nowrap">'
                f'<span style="font-size:11px;font-weight:700;color:#374151">{item["name"]}</span>'
                f'<span style="font-size:11px;font-weight:600;color:#111827;font-family:monospace">{close_s}</span>'
                f'<span style="font-size:10px;font-weight:700;background:{bg_pill};color:{clr};'
                f'padding:1px 6px;border-radius:10px">{arr} {pct_s}</span>'
                f'{spark}'
                f'</div>'
            )
        border = "" if is_last else "border-bottom:1px solid #F3F4F6;"
        rows_html += (
            f'<div style="display:flex;align-items:center;gap:0;'
            f'padding:6px 0;{border}">'
            f'<span style="font-size:9px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.6px;color:#B0B7C3;min-width:62px;flex-shrink:0">{label}</span>'
            f'<div style="width:1px;background:#E5E7EB;align-self:stretch;margin:0 10px 0 0;flex-shrink:0"></div>'
            f'<div style="display:flex;align-items:center;flex-wrap:nowrap;overflow-x:auto">{items_html}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:12px;'
        f'padding:8px 14px;margin-bottom:4px">{rows_html}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# ── 3대 서비스 카드 ───────────────────────────
sec_title("서비스 상황")

stock_topic    = "—"
theme_topic    = "—"
debate_created = "—"
if session:
    if session.get("stock_debate"):
        t = session["stock_debate"].get("debate_topic", "—")
        stock_topic = (t[:80] + "…") if len(t) > 80 else t
    if session.get("theme_debate"):
        t = session["theme_debate"].get("debate_topic", "—")
        theme_topic = (t[:80] + "…") if len(t) > 80 else t
    debate_created = session.get("created_at", "—")

# 통합 데이터 리스트를 아규먼트로 넘겨 최신 뉴스 3개 프리뷰 추출
headline_previews = load_headline_preview(integrated_news, 3)

# ── Row 1: 토론 브리핑 (전체 너비) ─────────────
st.markdown(f"""
<div class="svc-card" style="--accent:#F97316">
    <div style="display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap">
        <div style="flex:1.2;min-width:200px">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                <span style="font-size:26px">💬</span>
                <div>
                    <div class="svc-card-title">토론 브리핑</div>
                    <div style="font-size:12px;color:#9CA3AF">Bull · Bear 에이전트 기반 주식 토론</div>
                </div>
                <div style="margin-left:auto">{badge("구동 중" if session else "대기 중", "ok" if session else "off")}</div>
            </div>
            <div class="svc-card-desc">
                불/베어 에이전트가 오늘의 핵심 종목·테마를 놓고 데이터 기반 토론을 펼치고,
                오케스트레이터가 최종 판정을 내립니다.
            </div>
            <div style="font-size:11px;color:#9CA3AF;margin-top:8px">
                생성: {debate_created[:16] if debate_created != "—" else "—"}
            </div>
        </div>
        <div style="flex:2;min-width:280px;display:flex;gap:10px">
            <div style="flex:1;background:#FFF7ED;border-radius:10px;padding:12px">
                <div style="font-size:10px;font-weight:700;color:#EA580C;text-transform:uppercase;
                letter-spacing:.8px;margin-bottom:6px">📌 오늘의 종목</div>
                <div style="font-size:12.5px;color:#374151;line-height:1.65">{stock_topic}</div>
            </div>
            <div style="flex:1;background:#F5F3FF;border-radius:10px;padding:12px">
                <div style="font-size:10px;font-weight:700;color:#7C3AED;text-transform:uppercase;
                letter-spacing:.8px;margin-bottom:6px">🌐 오늘의 테마</div>
                <div style="font-size:12.5px;color:#374151;line-height:1.65">{theme_topic}</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
_, link_col1 = st.columns([5, 1])
with link_col1:
    st.page_link("pages/1_Debate.py", label="자세히 보기", use_container_width=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# ── Row 2: 뉴스 번역기 (2) + 투자 퀴즈 (1) ────
c_news, c_quiz = st.columns([2, 1])

with c_news:
    preview_items = "".join(
        f'<div style="font-size:12px;color:#374151;padding:5px 0;'
        f'border-bottom:1px solid #EDE9FE;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
        f'<span style="color:#9CA3AF;font-size:10.5px">{p}&nbsp;·&nbsp;</span>{t}'
        f'</div>'
        for t, p in headline_previews
    ) if headline_previews else '<div style="font-size:12px;color:#9CA3AF">최신 통합 뉴스 데이터 없음</div>'

    st.markdown(f"""
    <div class="svc-card" style="--accent:#7C3AED">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
            <span style="font-size:24px">📰</span>
            <div class="svc-card-title">뉴스 번역기</div>
            <div style="margin-left:auto">{badge(news_status, news_kind)}</div>
        </div>
        <div class="svc-card-desc" style="margin-bottom:12px">
            어려운 금융 뉴스를 쉬운 말로 번역합니다. 금융 용어 해설과 3줄 요약을 제공합니다.
        </div>
        <div style="background:#F5F3FF;border-radius:10px;padding:12px">
            <div style="font-size:10px;font-weight:700;color:#7C3AED;text-transform:uppercase;
            letter-spacing:.8px;margin-bottom:8px">최신 헤드라인 프리뷰</div>
            {preview_items}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    _, link_col2 = st.columns([3, 1])
    with link_col2:
        st.page_link("pages/2_News_Translator.py", label="자세히 보기", use_container_width=True)

with c_quiz:
    st.markdown(f"""
    <div class="svc-card" style="--accent:#10B981">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
            <span style="font-size:24px">🧩</span>
            <div class="svc-card-title">투자 퀴즈</div>
            <div style="margin-left:auto">{badge(quiz_status, quiz_kind)}</div>
        </div>
        <div class="svc-card-desc" style="margin-bottom:12px">
            당일 뉴스 기반 OX 퀴즈로 금융 리터러시를 테스트하세요.
        </div>
        <div style="background:#ECFDF5;border-radius:10px;padding:12px">
            <div style="font-size:10px;font-weight:700;color:#059669;text-transform:uppercase;
            letter-spacing:.8px;margin-bottom:8px">오늘의 퀴즈</div>
            <div style="font-size:12.5px;color:#374151">🗓️ {now.strftime('%m월 %d일')} 퀴즈 모음</div>
            <div style="font-size:11px;color:#6B7280;margin-top:6px">뉴스 기반 문제 자동 연동<br>정답 해설로 경제 이슈 이해</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    _, link_col3 = st.columns([1, 1])
    with link_col3:
        st.page_link("pages/3_Quiz.py", label="자세히 보기", use_container_width=True)

# ── 서비스 안내 ───────────────────────────────
st.markdown('<div class="sec-title" style="margin-top:36px">서비스 구조</div>', unsafe_allow_html=True)

st.markdown("""
<div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:14px;padding:24px">
    <div style="display:flex;gap:0;align-items:stretch;flex-wrap:wrap">
        <div style="flex:1;min-width:180px;padding:0 20px 0 0;border-right:1px solid #F3F4F6">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#F97316;margin-bottom:10px">① 토론 주제 선정</div>
            <div style="font-size:13px;color:#374151;line-height:1.7">
                네이버 경제 뉴스 크롤링<br>
                → GPT가 종목·테마 분류<br>
                → 오늘의 토론 주제 확정
            </div>
        </div>
        <div style="flex:1;min-width:180px;padding:0 20px;border-right:1px solid #F3F4F6">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6366F1;margin-bottom:10px">② 데이터 수집</div>
            <div style="font-size:13px;color:#374151;line-height:1.7">
                시장 심리 (VKOSPI · 수급)<br>
                → 매크로 국면 (PCA · 마코프)<br>
                → 섹터 분석 (실적 · 밸류에이션)
            </div>
        </div>
        <div style="flex:1;min-width:180px;padding:0 20px;border-right:1px solid #F3F4F6">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#10B981;margin-bottom:10px">③ 에이전트 토론</div>
            <div style="font-size:13px;color:#374151;line-height:1.7">
                🐂 불 에이전트 (낙관)<br>
                🐻 베어 에이전트 (비관)<br>
                데이터 기반 의견 대결
            </div>
        </div>
        <div style="flex:1;min-width:180px;padding:0 0 0 20px">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#EF4444;margin-bottom:10px">④ 최종 판정</div>
            <div style="font-size:13px;color:#374151;line-height:1.7">
                오케스트레이터 종합<br>
                → 합의 강도 계산<br>
                → 투자 판단 콘텐츠 생성
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)