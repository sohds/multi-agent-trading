"""
Global CSS styles and HTML helper functions for the dashboard.
Light theme with orange accent.
"""

import streamlit as st

GLOBAL_CSS = """
<style>
/* ── Base ── */
.main .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px; }

/* ── Service Card (Landing) ── */
.svc-card {
    background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 18px;
    padding: 28px 28px 22px; position: relative; overflow: hidden;
    transition: box-shadow .25s, transform .2s; cursor: pointer;
}
.svc-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
    background: var(--accent, #F97316); border-radius: 18px 18px 0 0;
}
.svc-card:hover { box-shadow: 0 16px 48px rgba(249,115,22,.1); transform: translateY(-2px); }
.svc-card-icon  { font-size: 36px; display: block; margin-bottom: 14px; }
.svc-card-title { font-size: 20px; font-weight: 800; color: #111827; margin-bottom: 6px; }
.svc-card-desc  { font-size: 13.5px; color: #6B7280; line-height: 1.7; }
.svc-card-foot  {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 18px; padding-top: 14px; border-top: 1px solid #F3F4F6;
    font-size: 12px;
}
.svc-card-status { color: #9CA3AF; }
.svc-card-cta    { color: #F97316; font-weight: 700; }

/* ── Hero ── */
.hero { margin-bottom: 2rem; }
.hero-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: #F97316; margin-bottom: 6px; }
.hero-title { font-size: 32px; font-weight: 900; color: #111827; line-height: 1.2; margin: 0; }
.hero-sub   { font-size: 15px; color: #6B7280; margin-top: 8px; line-height: 1.65; }

/* ── Status strip ── */
.status-strip {
    display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
    background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 12px;
    padding: 10px 20px; margin-bottom: 28px; font-size: 12px;
}
.status-strip .sep { color: #D1D5DB; }
.status-k { color: #9CA3AF; }
.status-v { color: #111827; font-weight: 600; }
.status-v.live { color: #F97316; }
.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }
.dot-orange { background: #F97316; box-shadow: 0 0 6px rgba(249,115,22,.5); }
.dot-green  { background: #10B981; }
.dot-gray   { background: #D1D5DB; }

/* ── Debate topic card ── */
.debate-topic-card {
    background: linear-gradient(135deg, #FFF7ED 0%, #FEF3C7 100%);
    border: 1.5px solid #FED7AA; border-radius: 16px; padding: 26px;
}
.debate-type-lbl {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1.2px; margin-bottom: 8px;
}
.type-stock { color: #EA580C; }
.type-theme { color: #7C3AED; }
.debate-topic-text {
    font-size: 18px; font-weight: 700; color: #111827; line-height: 1.55;
    margin-bottom: 12px;
}
.debate-topic-meta { font-size: 12px; color: #92400E; }

/* ── Supporting data ── */
.support-panel {
    background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px; padding: 14px 16px;
}
.support-panel-title {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .8px; color: #9CA3AF; margin-bottom: 10px;
    display: flex; align-items: center; gap: 6px;
}
.support-kv { display: flex; justify-content: space-between; align-items: center;
    padding: 5px 0; border-bottom: 1px solid #F3F4F6; font-size: 12px; }
.support-kv:last-child { border-bottom: none; }
.support-key { color: #9CA3AF; }
.support-val { font-weight: 600; color: #111827; }
.support-val.pos { color: #059669; }
.support-val.neg { color: #DC2626; }
.support-val.neu { color: #D97706; }

/* ── Agent cards (Bull / Bear) ── */
.agent-card {
    background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 14px;
    padding: 22px; height: 100%;
}
.agent-card.bull { border-top: 3px solid #10B981; }
.agent-card.bear { border-top: 3px solid #EF4444; }
.agent-lbl { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.bull .agent-lbl { color: #059669; }
.bear .agent-lbl { color: #DC2626; }
.agent-stance {
    font-size: 20px; font-weight: 800; margin-bottom: 10px;
    display: flex; align-items: center; gap: 8px;
}
.bull .agent-stance { color: #059669; }
.bear .agent-stance { color: #DC2626; }
.agent-summary { font-size: 13.5px; color: #374151; line-height: 1.75; }
.agent-signals { margin-top: 14px; }
.agent-signal-item {
    font-size: 12px; color: #6B7280; padding: 4px 0;
    border-bottom: 1px solid #F9FAFB; display: flex; align-items: center; gap: 6px;
}
.agent-signal-item:last-child { border: none; }

/* ── Placeholder agent card ── */
.agent-placeholder {
    border: 2px dashed #E5E7EB; border-radius: 14px; padding: 28px;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    text-align: center; min-height: 200px;
}
.agent-placeholder-icon { font-size: 32px; margin-bottom: 10px; opacity: .4; }
.agent-placeholder-text { font-size: 13px; color: #9CA3AF; line-height: 1.6; }

/* ── Verdict card ── */
.verdict-card {
    background: #111827; border-radius: 16px; padding: 28px; color: white;
    position: relative; overflow: hidden;
}
.verdict-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
    background: linear-gradient(90deg, #F97316, #FB923C);
}
.verdict-pretitle { font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; color: #6B7280; margin-bottom: 10px; }
.verdict-text { font-size: 17px; font-weight: 600; color: #F9FAFB; line-height: 1.7; }
.verdict-agreement { margin-top: 14px; padding-top: 14px; border-top: 1px solid #1F2937;
    font-size: 12px; color: #F97316; display: flex; align-items: center; gap: 6px; }

/* ── News card ── */
.news-card {
    background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px;
    overflow: hidden; transition: box-shadow .2s, transform .15s;
    display: flex; flex-direction: column; height: 100%;
}
.news-card:hover { box-shadow: 0 8px 28px rgba(0,0,0,.08); transform: translateY(-1px); }
.news-img-wrap { width: 100%; height: 150px; overflow: hidden; background: #F3F4F6;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.news-img-wrap img { width: 100%; height: 100%; object-fit: cover; }
.news-img-placeholder { font-size: 28px; opacity: .3; }
.news-body { padding: 14px 16px; flex: 1; display: flex; flex-direction: column; }
.news-meta { font-size: 11px; color: #9CA3AF; margin-bottom: 6px;
    display: flex; align-items: center; gap: 6px; }
.news-press { font-weight: 600; color: #6B7280; }
.news-title { font-size: 13.5px; font-weight: 700; color: #111827; line-height: 1.5;
    margin-bottom: 8px; flex: 1;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.news-lede { font-size: 12px; color: #6B7280; line-height: 1.6; margin-bottom: 10px;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.news-cluster { font-size: 10px; color: #F97316; font-weight: 600; }
.news-footer { padding: 10px 16px 14px; border-top: 1px solid #F3F4F6;
    display: flex; gap: 8px; }

/* ── Translation result ── */
.translate-result {
    background: #FFFBF7; border: 1.5px solid #FED7AA; border-radius: 12px; padding: 20px;
    margin-top: 8px;
}
.translate-result-title { font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .8px; color: #EA580C; margin-bottom: 10px; }
.translate-result-body { font-size: 14px; color: #374151; line-height: 1.8; }
.term-item {
    background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px;
    padding: 10px 14px; margin: 6px 0;
}
.term-name { font-size: 13px; font-weight: 700; color: #EA580C; margin-bottom: 3px; }
.term-def  { font-size: 12.5px; color: #374151; line-height: 1.6; }

/* ── Quiz card ── */
.quiz-card {
    background: #FFF7ED; border: 1.5px solid #FED7AA; border-radius: 16px; padding: 28px;
}
.quiz-card-label { font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .8px; color: #F97316; margin-bottom: 10px; }
.quiz-card-q { font-size: 19px; font-weight: 700; color: #111827; line-height: 1.6; }
.quiz-opt {
    background: #FFFFFF; border: 1.5px solid #E5E7EB; border-radius: 10px;
    padding: 13px 18px; margin: 8px 0; font-size: 14px; color: #374151;
    transition: border-color .15s, background .15s; cursor: pointer;
}
.quiz-opt:hover { border-color: #F97316; background: #FFF7ED; }
.quiz-opt.correct { border-color: #10B981; background: #ECFDF5; color: #065F46; font-weight: 600; }
.quiz-opt.wrong   { border-color: #EF4444; background: #FEF2F2; color: #991B1B; }

/* ── Badges ── */
.bdg {
    display: inline-flex; align-items: center; gap: 3px;
    padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; letter-spacing: .2px;
}
.bdg-ok     { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
.bdg-wip    { background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
.bdg-off    { background: #F9FAFB; color: #9CA3AF; border: 1px solid #E5E7EB; }
.bdg-orange { background: #FFF7ED; color: #EA580C; border: 1px solid #FED7AA; }
.bdg-bull   { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
.bdg-bear   { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
.bdg-neu    { background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }

/* ── Section title ── */
.sec-title {
    font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.2px;
    color: #9CA3AF; margin: 28px 0 14px;
    display: flex; align-items: center; gap: 8px;
}
.sec-title::after { content: ''; flex: 1; height: 1px; background: #F3F4F6; }

/* ── Callout ── */
.callout { background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px;
    padding: 12px 16px; font-size: 13px; color: #1E40AF; margin: 10px 0; line-height: 1.6; }
.callout-orange { background: #FFF7ED; border-color: #FED7AA; color: #9A3412; }
.callout-success { background: #ECFDF5; border-color: #A7F3D0; color: #065F46; }
.callout-warn { background: #FFFBEB; border-color: #FDE68A; color: #92400E; }

/* ── Tag ── */
.tag { display: inline-block; background: #FFF7ED; color: #EA580C;
    border: 1px solid #FED7AA; border-radius: 6px; padding: 2px 8px; font-size: 11px; margin: 2px; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background: #FFFFFF !important; border-right: 1px solid #F3F4F6; }
.sidebar-top { text-align: center; padding: 20px 0 16px; border-bottom: 1px solid #F3F4F6; margin-bottom: 14px; }
.sidebar-logo    { font-size: 36px; display: block; margin-bottom: 8px; }
.sidebar-name    { font-size: 15px; font-weight: 800; color: #111827; }
.sidebar-tagline { font-size: 11px; color: #9CA3AF; margin-top: 3px; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #E5E7EB; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #D1D5DB; }

/* ── Custom HTML buttons ── */
.btn {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 8px 20px; border-radius: 7px;
    font-size: 13px; font-weight: 500; cursor: pointer;
    transition: background 150ms ease, border-color 150ms ease, color 150ms ease;
    text-decoration: none !important; white-space: nowrap;
    line-height: 1.4; border: 1px solid transparent; box-sizing: border-box;
}
.btn-arr {
    display: inline-block;
    transition: transform 150ms ease;
}
.btn:hover .btn-arr { transform: translateX(2px); }
/* ghost — neutral (Notion/Linear/Vercel secondary style) */
.btn-ghost { background: #FFFFFF; border-color: #E5E7EB; color: #374151; }
.btn-ghost:hover { background: #F9FAFB; border-color: #D1D5DB; color: #111827; }
/* ghost — purple */
.btn-ghost-purple { background: #FFFFFF; border-color: #C4B5FD; color: #7C3AED; }
.btn-ghost-purple:hover { background: #F5F3FF; border-color: #7C3AED; color: #6D28D9; }
/* ghost — orange */
.btn-ghost-orange { background: #FFFFFF; border-color: #FED7AA; color: #EA580C; }
.btn-ghost-orange:hover { background: #FFF7ED; border-color: #F97316; color: #C2410C; }

/* ── Streamlit button overrides — unified 13 px sizing ── */
[data-testid="stButton"] > button,
[data-testid="stPageLink"] a,
[data-testid="stLinkButton"] a,
.stLinkButton a {
    font-size: 13px !important;
    padding: 0.45rem 1.25rem !important;
    font-weight: 500 !important;
    min-height: 36px !important;
    line-height: 1.4 !important;
}

/* Primary: pill shape, bolder weight */
[data-testid="stButton"] > button[kind="primary"] {
    border-radius: 9999px !important;
    font-weight: 600 !important;
    transition: filter 150ms ease !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover { filter: brightness(0.92) !important; }

/* Secondary Streamlit button: Notion-like */
[data-testid="stButton"] > button[kind="secondary"] {
    border-radius: 7px !important;
    background: #FFFFFF !important;
    border: 1px solid #E5E7EB !important;
    color: #374151 !important;
    transition: background 150ms ease, border-color 150ms ease, color 150ms ease !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: #F9FAFB !important;
    border-color: #D1D5DB !important;
    color: #111827 !important;
    filter: none !important;
}

/* Link buttons: Notion-like secondary */
[data-testid="stLinkButton"] a,
.stLinkButton a {
    border-radius: 7px !important;
    background: #FFFFFF !important;
    border: 1px solid #E5E7EB !important;
    color: #374151 !important;
    transition: background 150ms ease, border-color 150ms ease, color 150ms ease !important;
}
[data-testid="stLinkButton"] a:hover,
.stLinkButton a:hover {
    background: #F9FAFB !important;
    border-color: #D1D5DB !important;
    color: #111827 !important;
    filter: none !important;
}

/* Page links: borderless, right-aligned, small text */
[data-testid="stPageLink"] a {
    display: inline-flex !important;
    justify-content: flex-end !important;
    align-items: center !important;
    border-radius: 7px !important;
    color: #EA580C !important;
    background: transparent !important;
    border: none !important;
    padding: 0.28rem 0.5rem !important;
    min-height: 26px !important;
    width: 100% !important;
    transition: color 150ms ease !important;
    letter-spacing: 0.2px !important;
}
[data-testid="stPageLink"] a,
[data-testid="stPageLink"] a * {
    font-size: 10px !important;
    font-weight: 600 !important;
}
[data-testid="stPageLink"] a::after {
    content: '→';
    margin-left: 4px;
    display: inline-block;
    transition: transform 150ms ease;
}
[data-testid="stPageLink"] a:hover {
    background: transparent !important;
    color: #C2410C !important;
    filter: none !important;
}
[data-testid="stPageLink"] a:hover::after {
    transform: translateX(3px);
}
</style>
"""


def inject_css() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def badge(text: str, kind: str = "ok") -> str:
    cls = {"ok": "bdg-ok", "wip": "bdg-wip", "off": "bdg-off",
           "orange": "bdg-orange", "bull": "bdg-bull", "bear": "bdg-bear", "neu": "bdg-neu"
           }.get(kind, "bdg-off")
    return f'<span class="bdg {cls}">{text}</span>'


def sec_title(text: str) -> None:
    st.markdown(f'<div class="sec-title">{text}</div>', unsafe_allow_html=True)


def callout(text: str, kind: str = "info") -> None:
    cls = {"info": "callout", "orange": "callout callout-orange",
           "success": "callout callout-success", "warn": "callout callout-warn"}.get(kind, "callout")
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)
