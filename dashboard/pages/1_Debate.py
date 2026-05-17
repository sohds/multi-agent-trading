"""
토론 브리핑 — 메인 서비스 페이지

구조:
  [오늘의 토론 주제] ← debate/
    ↓
  [입력 데이터 패널] ← market/ + macro/ + sector/ (하위 지원 에이전트)
    ↓
  [불 에이전트 vs 베어 에이전트] ← bull-bear/ (LLM 연결 후 활성화)
    ↓
  [오케스트레이터 최종 판정]
"""

import streamlit as st
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.styles import inject_css, badge, sec_title, callout

st.set_page_config(page_title="토론 브리핑 | AI 주식 브리핑", page_icon="💬", layout="wide")
inject_css()

# ── 경로 ─────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SESSION_JSON = os.path.join(ROOT, "config", "session.json")

# ── 데이터 로드 ───────────────────────────────

def load_session() -> dict | None:
    if os.path.exists(SESSION_JSON):
        try:
            return json.load(open(SESSION_JSON, encoding="utf-8"))
        except Exception:
            return None
    return None

# 지원 에이전트 데이터 로드 함수 (모듈 연결 시 교체)
def load_market_data() -> dict | None:
    """market/ 모듈의 MarketSentimentCollector 결과를 반환합니다."""
    return None

def load_macro_data() -> dict | None:
    """macro/ 모듈의 run_macro_agent() 결과를 반환합니다."""
    return None

def load_sector_data(ticker: str, etf: str) -> dict | None:
    """sector/ 모듈의 run_sector_agent() 결과를 반환합니다."""
    return None

# 에이전트 토론 함수 (LLM 연결 시 교체)
def run_bull_agent(topic: dict, market: dict, macro: dict, sector: dict) -> dict | None:
    """
    불 에이전트 (낙관 프레임) — 토론 주제에 대해 매수 논거를 생성합니다.

    실제 연동 예시:
        from bull_bear.agents.bull_agent import BullAgent
        return BullAgent().analyze(topic=topic, market=market, macro=macro, sector=sector)

    반환 구조:
    {
        "stance": "bullish" | "neutral",
        "summary": str,          # 150자 내외 요약
        "key_signals": list[str], # 주요 근거 지표 목록
        "confidence": float,     # 0.0 ~ 1.0
    }
    """
    return None

def run_bear_agent(topic: dict, market: dict, macro: dict, sector: dict) -> dict | None:
    """
    베어 에이전트 (비관 프레임) — 토론 주제에 대해 매도/관망 논거를 생성합니다.
    반환 구조는 run_bull_agent와 동일합니다.
    """
    return None

def run_orchestrator(bull: dict, bear: dict, topic: dict) -> dict | None:
    """
    오케스트레이터 — 불/베어 에이전트 의견을 종합해 최종 판정을 내립니다.

    실제 연동 예시:
        from orchestrator.agent import Orchestrator
        return Orchestrator().synthesize(bull=bull, bear=bear, topic=topic)

    반환 구조:
    {
        "verdict": str,           # 최종 판정 문장
        "agreement_score": str,   # 예: "2/3"
        "agreement_level": str,   # "높음" | "중간" | "낮음"
        "confidence": float,
    }
    """
    return None


# ─────────────────────────────────────────────
session = load_session()

# ── 헤더 ──────────────────────────────────────
st.markdown("""
<div style="margin-bottom:1.5rem">
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
    letter-spacing:1.2px;color:#F97316;margin-bottom:6px">Daily Debate</div>
    <div style="font-size:28px;font-weight:900;color:#111827">토론 브리핑</div>
    <div style="font-size:14px;color:#6B7280;margin-top:6px">
        불(Bull) · 베어(Bear) 에이전트가 오늘의 핵심 뉴스로 토론하고, 오케스트레이터가 최종 판정을 내립니다.
    </div>
</div>
""", unsafe_allow_html=True)

if not session:
    callout(
        "📭 오늘의 토론 주제가 아직 생성되지 않았습니다. "
        "<code>python debate/debate_topic_agent.py</code>를 먼저 실행하세요.",
        kind="warn",
    )
    st.stop()

stock_d = session.get("stock_debate") or {}
theme_d = session.get("theme_debate") or {}
created = session.get("created_at", "—")

# ── 종목 선택 탭 ──────────────────────────────
tab_stock, tab_theme = st.tabs([
    f"📌 종목토론 — {stock_d.get('stock_name', '—')}",
    f"🌐 테마토론 — {theme_d.get('sector', '—')}",
])

for tab, debate in [(tab_stock, stock_d), (tab_theme, theme_d)]:
    with tab:
        if not debate:
            callout("이 탭의 토론 주제가 없습니다.", kind="warn")
            continue

        ticker    = debate.get("ticker")
        etf       = debate.get("sector_etf", "")
        topic_txt = debate.get("debate_topic", "—")
        news      = debate.get("news", {})
        d_type    = debate.get("debate_type", "stock")
        sector    = debate.get("sector", "—")
        sname     = debate.get("stock_name")

        # ① 오늘의 토론 주제 ─────────────────────
        type_cls   = "type-stock" if d_type == "stock" else "type-theme"
        type_label = "종목토론 (Stock)" if d_type == "stock" else "테마토론 (Theme)"
        meta_parts = []
        if sname:   meta_parts.append(f"종목: {sname} ({ticker})")
        if sector:  meta_parts.append(f"섹터: {sector}")
        if etf:     meta_parts.append(f"ETF: {etf}")
        meta_str = "&nbsp;&nbsp;·&nbsp;&nbsp;".join(meta_parts)

        st.markdown(f"""
        <div class="debate-topic-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
                <div class="debate-type-lbl {type_cls}">{type_label}</div>
                <div style="font-size:11px;color:#92400E">생성: {created[:16] if created != "—" else "—"}</div>
            </div>
            <div class="debate-topic-text">{topic_txt}</div>
            <div class="debate-topic-meta">{meta_str}</div>
        </div>
        """, unsafe_allow_html=True)

        # 원문 뉴스 링크
        if news.get("url") or news.get("title"):
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            nc1, nc2 = st.columns([4, 1])
            with nc1:
                press = news.get("press", "")
                pub   = news.get("published_at", "")[:16] if news.get("published_at") else ""
                lede  = news.get("lede", "")
                st.markdown(
                    f'<div style="font-size:12px;color:#6B7280">'
                    f'📰 <strong style="color:#374151">{news.get("title","")}</strong>'
                    f'&nbsp;·&nbsp;{press}&nbsp;·&nbsp;{pub}'
                    f'</div>'
                    f'<div style="font-size:12px;color:#9CA3AF;margin-top:2px">{lede}</div>',
                    unsafe_allow_html=True,
                )
            with nc2:
                if news.get("url"):
                    st.markdown(
                        f'<div style="display:flex;justify-content:flex-end">'
                        f'<a href="{news["url"]}" target="_blank" class="btn btn-ghost-orange">'
                        f'원문 보기 <span class="btn-arr">→</span></a>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        st.divider()

        # ② 입력 데이터 패널 (지원 에이전트) ──────
        sec_title("입력 데이터 — 에이전트 분석 컨텍스트")

        market_data = load_market_data()
        macro_data  = load_macro_data()
        sector_data = load_sector_data(ticker or "", etf)

        dp1, dp2, dp3 = st.columns(3)

        with dp1:
            mkt_score = market_data.get("analysis", {}).get("sentiment_score") if market_data else None
            mkt_label = market_data.get("analysis", {}).get("sentiment_label", "—") if market_data else "—"
            vkospi    = market_data.get("raw_data", {}).get("vkospi", {}).get("value") if market_data else None
            st.markdown(f"""
            <div class="support-panel">
                <div class="support-panel-title">🌡️ 시장 심리</div>
                <div class="support-kv">
                    <span class="support-key">심리 점수</span>
                    <span class="support-val {'pos' if (mkt_score or 0)>0.5 else 'neg' if (mkt_score or 0)<0.3 else 'neu'}">{f"{mkt_score:.2f}" if mkt_score else "—"}</span>
                </div>
                <div class="support-kv">
                    <span class="support-key">심리 레이블</span>
                    <span class="support-val">{mkt_label}</span>
                </div>
                <div class="support-kv">
                    <span class="support-key">VKOSPI</span>
                    <span class="support-val {'neg' if (vkospi or 0)>25 else 'pos'}">{f"{vkospi:.1f}" if vkospi else "—"}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with dp2:
            regime = "—"
            fsi    = "—"
            risk   = "—"
            if macro_data:
                probs  = macro_data.get("quantitative_models", {}).get("regime_probabilities", {})
                p_n    = probs.get("state_0_normal", 0)
                p_c    = probs.get("state_1_caution", 0)
                p_k    = probs.get("state_2_crisis", 0)
                regime = "정상" if p_n >= .7 else ("주의" if p_c >= .5 else "위기" if p_k >= .5 else "혼조")
                fsi_v  = macro_data.get("quantitative_models", {}).get("fsi_factor_score")
                fsi    = f"{fsi_v:.3f}" if fsi_v is not None else "—"
                risk_raw = macro_data.get("objective_analysis", {}).get("risk_assessment", "")
                risk = risk_raw.split("수준")[0].strip() + " 수준" if "수준" in risk_raw else risk_raw[:15]
            st.markdown(f"""
            <div class="support-panel">
                <div class="support-panel-title">🏛️ 매크로 국면</div>
                <div class="support-kv">
                    <span class="support-key">현재 국면</span>
                    <span class="support-val {'pos' if regime=='정상' else 'neg' if regime=='위기' else 'neu'}">{regime}</span>
                </div>
                <div class="support-kv">
                    <span class="support-key">FSI 점수</span>
                    <span class="support-val">{fsi}</span>
                </div>
                <div class="support-kv">
                    <span class="support-key">위험 수준</span>
                    <span class="support-val">{risk}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with dp3:
            sd_trend = "—"
            per_lbl  = "—"
            yoy_op   = "—"
            if sector_data:
                streak   = sector_data.get("supply_demand", {}).get("streak", {}) if sector_data.get("supply_demand") else {}
                inst_t   = streak.get("institutional_5d_trend", "—")
                sd_trend = inst_t
                per_l    = sector_data.get("valuation", {}).get("per_label", "—") if sector_data.get("valuation") else "—"
                per_lbl  = per_l[:12] if per_l != "—" else "—"
                yoy_v    = sector_data.get("earnings", {}).get("yoy", {}).get("op_income_chg") if sector_data.get("earnings") else None
                yoy_op   = f"{yoy_v:+.1f}%" if yoy_v is not None else "—"
            st.markdown(f"""
            <div class="support-panel">
                <div class="support-panel-title">🏭 섹터 데이터</div>
                <div class="support-kv">
                    <span class="support-key">기관 5일 추세</span>
                    <span class="support-val {'pos' if '매수' in sd_trend else 'neg' if '매도' in sd_trend else ''}">{sd_trend}</span>
                </div>
                <div class="support-kv">
                    <span class="support-key">PER 위치</span>
                    <span class="support-val">{per_lbl}</span>
                </div>
                <div class="support-kv">
                    <span class="support-key">영업이익 YoY</span>
                    <span class="support-val {'pos' if '+' in yoy_op else 'neg' if '-' in yoy_op else ''}">{yoy_op}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        if not any([market_data, macro_data, sector_data]):
            callout(
                "지원 에이전트 데이터가 연결되지 않았습니다. "
                "market/ · macro/ · sector/ 모듈을 실행하면 이 패널에 실시간 데이터가 표시됩니다.",
                kind="orange",
            )

        st.divider()

        # ③ 불 vs 베어 에이전트 ───────────────────
        sec_title("에이전트 토론")

        bull_result = run_bull_agent(debate, market_data, macro_data, sector_data)
        bear_result = run_bear_agent(debate, market_data, macro_data, sector_data)

        bc1, bc2 = st.columns(2)

        def render_agent_card(col, agent_type: str, result: dict | None):
            is_bull = agent_type == "bull"
            icon   = "🐂" if is_bull else "🐻"
            label  = "불 (Bull) 에이전트" if is_bull else "베어 (Bear) 에이전트"
            stance_default = "낙관 (Bullish)" if is_bull else "비관 (Bearish)"
            css    = "bull" if is_bull else "bear"

            with col:
                if result:
                    stance    = result.get("stance", stance_default)
                    summary   = result.get("summary", "—")
                    signals   = result.get("key_signals", [])
                    conf      = result.get("confidence")
                    conf_str  = f"{conf*100:.0f}%" if conf is not None else "—"

                    signals_html = "".join(
                        f'<div class="agent-signal-item">▸ {s}</div>' for s in signals
                    ) if signals else '<div class="agent-signal-item" style="color:#D1D5DB">근거 데이터 없음</div>'

                    st.markdown(f"""
                    <div class="agent-card {css}">
                        <div class="agent-lbl">{icon} {label}</div>
                        <div class="agent-stance">{stance}</div>
                        <div class="agent-summary">{summary}</div>
                        <div class="agent-signals">
                            <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                            letter-spacing:.8px;color:#9CA3AF;margin:12px 0 6px">주요 근거 신호</div>
                            {signals_html}
                        </div>
                        <div style="margin-top:14px;font-size:11px;color:#9CA3AF">신뢰도: {conf_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    agent_color = "#10B981" if is_bull else "#EF4444"
                    st.markdown(f"""
                    <div class="agent-placeholder">
                        <div class="agent-placeholder-icon">{icon}</div>
                        <div style="font-size:13px;font-weight:700;color:#374151;margin-bottom:6px">{label}</div>
                        <div class="agent-placeholder-text">
                            LLM 연결 후 이 자리에<br>
                            <strong style="color:{agent_color}">{'낙관' if is_bull else '비관'} 관점</strong>의 토론 논거가 표시됩니다.
                        </div>
                        <div style="margin-top:16px">
                            {badge('연결 대기 중', 'off')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        render_agent_card(bc1, "bull", bull_result)
        render_agent_card(bc2, "bear", bear_result)

        st.divider()

        # ④ 오케스트레이터 최종 판정 ──────────────
        sec_title("최종 판정")

        orch = run_orchestrator(bull_result, bear_result, debate) if (bull_result and bear_result) else None

        if orch:
            verdict   = orch.get("verdict", "—")
            agreement = orch.get("agreement_score", "—")
            level     = orch.get("agreement_level", "—")
            conf_o    = orch.get("confidence")
            conf_str_o = f"{conf_o*100:.0f}%" if conf_o is not None else "—"

            st.markdown(f"""
            <div class="verdict-card">
                <div class="verdict-pretitle">⚖️ 오케스트레이터 최종 판정</div>
                <div class="verdict-text">{verdict}</div>
                <div class="verdict-agreement">
                    합의 강도 {agreement} &nbsp;·&nbsp; 합의 수준: {level} &nbsp;·&nbsp; 신뢰도: {conf_str_o}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:16px;
            padding:32px;text-align:center">
                <div style="font-size:28px;margin-bottom:10px;opacity:.4">⚖️</div>
                <div style="font-size:14px;font-weight:700;color:#374151;margin-bottom:6px">
                    오케스트레이터 최종 판정
                </div>
                <div style="font-size:13px;color:#9CA3AF;line-height:1.7">
                    불/베어 에이전트 연결 후 이 자리에<br>
                    합의 강도·판정 근거와 함께 최종 판정이 표시됩니다.
                </div>
                <div style="margin-top:16px">{badge('연결 대기 중', 'off')}</div>
            </div>
            """, unsafe_allow_html=True)
