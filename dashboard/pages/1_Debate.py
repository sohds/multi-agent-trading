"""
토론 브리핑 — 메인 서비스 페이지 (에이전트 연결)

구조:
  [오늘의 토론 주제] ← config/session.json (debate_topic_agent 저장)
  [입력 데이터 패널] ← macro / sector / sentiment (토론 실행 후 채워짐)
  [🚀 토론 시작] 버튼 → 라운드별 Bull/Bear 채팅 스트리밍
  [사이드 패널] ← 왼쪽 채팅 버블 | 오른쪽 최종 판정
"""

import json
import os
import sys

import streamlit as st

# ── sys.path 설정 ─────────────────────────────────────────────
_PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
_DASH_DIR  = os.path.dirname(_PAGES_DIR)       # dashboard/
ROOT       = os.path.dirname(_DASH_DIR)        # project root

for _mod in ("bull-bear", "macro", "sector", "market"):
    _p = os.path.join(ROOT, _mod)
    if _p not in sys.path:
        sys.path.insert(0, _p)

# dashboard/utils/styles.py — sys.path에 dashboard/ 추가 없이 직접 로드
# (macro/sector/market 모두 utils/ 하위에 logger.py 등을 가지므로 sys.path 충돌 방지)
import importlib.util as _ilu
_styles_spec = _ilu.spec_from_file_location("_dashboard_styles", os.path.join(_DASH_DIR, "utils", "styles.py"))
_styles_mod  = _ilu.module_from_spec(_styles_spec)
_styles_spec.loader.exec_module(_styles_mod)
inject_css = _styles_mod.inject_css
badge      = _styles_mod.badge
sec_title  = _styles_mod.sec_title
callout    = _styles_mod.callout

# ── 에이전트 임포트 ──────────────────────────────────────────
try:
    from package_builder import build_input_package            # noqa: E402
    from agents.bull_agent import run_bull_agent as _bull_fn   # noqa: E402
    from agents.bear_agent import run_bear_agent as _bear_fn   # noqa: E402
    _AGENTS_OK  = True
    _AGENTS_ERR = ""
except ImportError as _e:
    _AGENTS_OK  = False
    _AGENTS_ERR = str(_e)

st.set_page_config(page_title="토론 브리핑 | AI 주식 브리핑", page_icon="💬", layout="wide")
inject_css()

st.markdown("""
<style>
/* 사이드바 expander 제목 폰트 크기 */
section[data-testid="stSidebar"] details summary p,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary p {
    font-size: 13px !important;
}
/* 토론 시작·주제 생성 버튼: rounded-rect, ghost-orange */
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
/* 보조 버튼: rounded-rect, neutral */
[data-testid="stButton"] > button[kind="secondary"],
[data-testid="stButton"] > button[kind="secondary"] * {
    font-size: 14px !important;
    font-weight: 600 !important;
}
[data-testid="stButton"] > button[kind="secondary"] {
    border-radius: 10px !important;
    padding: 0.45rem 1.4rem !important;
    min-height: 38px !important;
}
</style>
""", unsafe_allow_html=True)

# ── 상수 ─────────────────────────────────────────────────────
_CONFIG_DIR       = os.path.join(ROOT, "config")
os.makedirs(_CONFIG_DIR, exist_ok=True)
SESSION_JSON      = os.path.join(_CONFIG_DIR, "session.json")
SUPPORT_JSON      = os.path.join(_CONFIG_DIR, "support_data.json")
MODEL             = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
NEUTRAL_THRESHOLD = 0.05

# ── 사이드바: 기술적 지표 가이드 ──────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                letter-spacing:1.2px;color:#F97316;margin-bottom:4px">
        Indicator Guide
    </div>
    <div style="font-size:18px;font-weight:800;color:#111827;margin-bottom:14px">
        지표 용어 설명
    </div>
    """, unsafe_allow_html=True)

    _INDICATOR_GROUPS = [
        ("📈 추세 지표", [
            ("이동평균선", "MA 5/20/60/120/200",
             "일정 기간 종가 평균. 단기(5·20일)와 장기(60·120·200일)를 비교해 추세 방향을 파악합니다."),
            ("골든크로스", "MA20 ↑ MA60",
             "단기 MA20이 장기 MA60을 상향 돌파할 때 발생. 상승 전환 신호로 해석됩니다."),
            ("데드크로스", "MA20 ↓ MA60",
             "단기 MA20이 장기 MA60을 하향 돌파할 때 발생. 하락 전환 신호로 해석됩니다."),
        ]),
        ("⚡ 모멘텀 지표", [
            ("RSI", "14일 기준",
             "과매수·과매도 측정. RSI > 70이면 과매수(하락 경계), RSI < 30이면 과매도(반등 기대) 구간입니다."),
            ("MACD", "12·26·9일",
             "단기·장기 지수이동평균 차이로 추세 변화를 포착. MACD선이 시그널선을 상향 돌파하면 매수 신호, 하향 돌파하면 매도 신호입니다."),
        ]),
        ("🎯 변동성 지표", [
            ("볼린저 밴드", "20일, ±2σ",
             "중심선(MA20) ± 표준편차 2배로 가격 범위를 표시. 상단 근접 시 과열, 하단 근접 시 과매도 가능성을 나타냅니다."),
            ("이격도", "20일 기준",
             "현재가 ÷ MA20 × 100. 100 초과면 평균 대비 고평가, 100 미만이면 저평가 상태입니다."),
        ]),
        ("📊 거래량 지표", [
            ("거래량 변화율", "5일 이동 비교",
             "최근 5일 평균 거래량을 직전 5일과 비교. 양수일수록 거래 참여도가 증가하는 추세입니다."),
            ("거래량 급등", "20일 평균 × 2배",
             "당일 거래량이 20일 평균의 2배를 초과하면 급등 판정. 강한 수급 변화나 이슈 발생을 시사합니다."),
        ]),
        ("🛡️ 지지·저항", [
            ("지지선", "최근 20일 저가",
             "최근 20거래일 중 최저가 기반. 주가가 이 수준에서 반등할 가능성이 있는 가격대입니다."),
            ("저항선", "최근 20일 고가",
             "최근 20거래일 중 최고가 기반. 주가가 이 수준에서 상승 둔화될 가능성이 있는 가격대입니다."),
        ]),
        ("💰 밸류에이션", [
            ("PER", "주가수익비율",
             "주가 ÷ EPS. 낮을수록 이익 대비 저평가. 3년 히스토리 하위 20% = 역사적 저평가 구간."),
            ("PBR", "주가순자산비율",
             "주가 ÷ 주당순자산. 1 미만이면 장부 가치 이하로 거래 중. 낮을수록 자산 대비 저평가."),
            ("EPS", "주당순이익 (원)",
             "순이익 ÷ 발행주식수. 기업 수익성 지표. YoY 증가 시 실적 개선, 감소 시 악화."),
            ("EPS YoY", "전년 대비 변화율",
             "EPS가 1년 전 대비 몇 % 변했는지. 양수=이익 증가, 음수=이익 감소."),
        ]),
        ("🏦 수급·심리", [
            ("외국인 순매수", "20d/60d/120d",
             "외국인이 특정 기간 동안 순매수(+) 또는 순매도(-) 한 금액(억원). 외국인 수급은 기관 방향과 함께 추세의 신뢰도를 높입니다."),
            ("외국인 연속 매수/매도", "최근 5거래일",
             "5거래일 중 순매수 일수와 순매도 일수. 예: 매도 4일 = 단기 매도 우위 지속."),
            ("기관 5일 수급", "기관합계",
             "최근 5거래일 기관 누적 순매수(억원). 양수=매수 우위, 음수=매도 우위."),
            ("VKOSPI", "한국판 공포지수",
             "옵션 시장에서 산출한 변동성 지수. 높을수록 시장 불안감 큼. 30 초과 시 공포 국면."),
            ("FSI", "금융스트레스지수",
             "KOSPI·환율·금리·스프레드를 PCA로 합산한 종합 스트레스 지수. 양수=스트레스 상승, 음수=안정."),
        ]),
        ("🌐 거시경제", [
            ("장단기 금리차", "10년물 - 3개월물",
             "양수=정상 곡선, 음수(역전)=경기침체 선행 신호로 해석됩니다."),
            ("신용 스프레드", "회사채AA- - 국채3년",
             "기업과 국가 간 금리 차이. 클수록 시장의 기업 신용위험 인식이 높음을 의미합니다."),
            ("시장 국면", "마코프 3-State",
             "FSI 기반 국면전환 모형. 정상(Normal) / 주의(Caution) / 위기(Crisis) 3단계 확률로 현재 거시환경을 진단합니다."),
        ]),
    ]

    for _group_title, _items in _INDICATOR_GROUPS:
        with st.expander(_group_title, expanded=False):
            for _name, _param, _desc in _items:
                st.markdown(f"""
                <div style="margin-bottom:10px">
                    <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:2px">
                        <span style="font-size:13px;font-weight:700;color:#1F2937">{_name}</span>
                        <span style="font-size:10px;font-weight:600;color:#F97316;
                                     background:#FFF7ED;padding:1px 6px;border-radius:4px;
                                     border:1px solid #FED7AA">{_param}</span>
                    </div>
                    <div style="font-size:12px;color:#6B7280;line-height:1.5">{_desc}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:16px;padding:10px 12px;background:#F0FDF4;border-radius:8px;
                border-left:3px solid #22C55E">
        <div style="font-size:11px;font-weight:700;color:#15803D;margin-bottom:4px">
            💡 에이전트 활용 방식
        </div>
        <div style="font-size:11px;color:#166534;line-height:1.5">
            Bull / Bear 에이전트는 위 지표를 입력 패키지로 받아 매수·매도 논거를 구성합니다.
            동일 지표도 에이전트 관점에 따라 상반된 해석이 가능합니다.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── 세션 상태 초기화 ─────────────────────────────────────────
for _k in ("debate_stock", "debate_theme"):
    if _k not in st.session_state:
        st.session_state[_k] = None


# ══════════════════════════════════════════════════════════════
# 헬퍼 함수
# ══════════════════════════════════════════════════════════════

def load_session() -> dict | None:
    if not os.path.exists(SESSION_JSON):
        return None
    try:
        data = json.load(open(SESSION_JSON, encoding="utf-8"))
        # 리스트로 저장된 경우 가장 최신 항목 사용
        if isinstance(data, list):
            data = data[-1] if data else None
        return data
    except Exception:
        return None


def load_support_data() -> dict:
    if not os.path.exists(SUPPORT_JSON):
        return {}
    try:
        return json.load(open(SUPPORT_JSON, encoding="utf-8")) or {}
    except Exception:
        return {}


def _classify(bull: dict, bear: dict) -> tuple[str, float]:
    if bull.get("error") or bear.get("error"):
        return "error", 0.0
    bc   = float(bull.get("confidence") or 0)
    berc = float(bear.get("confidence") or 0)
    diff = bc - berc
    if abs(diff) < NEUTRAL_THRESHOLD:
        return "neutral", diff
    return ("bullish" if diff > 0 else "bearish"), diff


_ORCH_PROMPT = """\
당신은 투자 토론의 오케스트레이터입니다.
Bull(매수)과 Bear(매도) 에이전트의 최종 논거와 confidence를 보고,
왜 해당 판정이 내려졌는지 **2~3문장**으로 설명하세요.

규칙:
- 승패를 가른 핵심 데이터·논거를 구체적으로 언급할 것
- 수치(confidence, 지표명)를 직접 인용할 것
- 반드시 한국어로 출력할 것
- 판정 결과(BULLISH/BEARISH/NEUTRAL)로 문장을 시작하지 말 것 (이미 UI에 표시됨)
- 순수 텍스트만 출력 (JSON, 마크다운 불필요)
"""


def _run_orchestrator(bull: dict, bear: dict, verdict: str, diff: float) -> str:
    """Bull/Bear 논거를 바탕으로 판정 이유를 한 문단으로 생성"""
    try:
        import os
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        winner   = "Bull" if verdict == "bullish" else ("Bear" if verdict == "bearish" else "동점(중립)")
        loser    = "Bear" if verdict == "bullish" else ("Bull" if verdict == "bearish" else "—")
        user_msg = (
            f"[판정 결과] {verdict.upper()} (confidence 차이: {diff:+.3f})\n"
            f"[승자] {winner}  [패자] {loser}\n\n"
            f"[Bull 최종 요약] {bull.get('summary', '없음')}\n"
            f"[Bull confidence] {bull.get('confidence', 0):.2f}\n"
            f"[Bull 논거]\n" +
            "\n".join(f"  - {a.get('claim','')}" for a in (bull.get("arguments") or [])) +
            f"\n\n[Bear 최종 요약] {bear.get('summary', '없음')}\n"
            f"[Bear confidence] {bear.get('confidence', 0):.2f}\n"
            f"[Bear 논거]\n" +
            "\n".join(f"  - {a.get('claim','')}" for a in (bear.get("arguments") or [])) +
            "\n\n위 정보를 바탕으로 판정 이유를 2~3문장으로 설명하세요."
        )
        resp = client.chat.completions.create(
            model=MODEL,
            max_completion_tokens=300,
            messages=[
                {"role": "system", "content": _ORCH_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"(판정 이유 생성 실패: {e})"


import tempfile as _tempfile
_SUPPORT_ERR_LOG = os.path.join(_tempfile.gettempdir(), "debate_support_errors.log")


def _log_err(tag: str, exc: Exception) -> None:
    import traceback
    try:
        with open(_SUPPORT_ERR_LOG, "a", encoding="utf-8") as _f:
            _f.write(f"\n=== {tag} ===\n{traceback.format_exc()}\n")
    except Exception:
        pass


def _load_macro() -> dict | None:
    try:
        from macro_agents.macro_agent import run_macro_agent  # noqa: E402
        return run_macro_agent()
    except Exception as e:
        _log_err("MACRO", e)
        return None


def _load_sector(ticker: str, ticker_name: str, sector_etf: str) -> dict | None:
    try:
        from sector_agents.sector_agent import run_sector_agent  # noqa: E402
        return run_sector_agent(ticker, ticker_name, sector_etf)
    except Exception as e:
        _log_err(f"SECTOR({ticker})", e)
        return None


def _load_market() -> dict | None:
    try:
        from market_collectors.sentiment_collector import MarketSentimentCollector  # noqa: E402
        raw = MarketSentimentCollector().analyze_sentiment()
        return {
            "sentiment_label": raw["analysis"]["sentiment_label"],
            "sentiment_score": raw["analysis"]["sentiment_score"],
            "confidence":      raw["analysis"]["confidence"],
            "risk_signal":     raw["analysis"]["risk_signal"],
            "vkospi":          raw["raw_data"]["vkospi"],
            "foreign_flow":    raw["raw_data"]["foreign_flow"],
            "market_momentum": raw["raw_data"]["market_momentum"],
            "reason":          raw.get("reason", ""),
        }
    except Exception as e:
        _log_err("MARKET", e)
        return None


# ── UI 렌더링 헬퍼 ────────────────────────────────────────────

def _chat_bubble_html(msg_type: str, rnd: int, data: dict) -> str:
    """Bull(왼쪽) / Bear(오른쪽) 말풍선 HTML 반환"""
    is_bull  = msg_type == "bull"
    label    = "🐂 Bull" if is_bull else "🐻 Bear"
    bg       = "#E8F5E9" if is_bull else "#FFEBEE"
    border   = "#4CAF50" if is_bull else "#EF5350"
    align    = "flex-start" if is_bull else "flex-end"
    radius   = "4px 18px 18px 18px" if is_bull else "18px 4px 18px 18px"
    name_col = "#2E7D32" if is_bull else "#C62828"
    name_align = "left" if is_bull else "right"

    if data.get("error"):
        body = f'<span style="color:#EF5350">오류: {data["error"]}</span>'
    else:
        summary = data.get("summary", "—")
        conf    = float(data.get("confidence") or 0)
        bar_w   = int(conf * 100)
        bar_col = "#4CAF50" if is_bull else "#EF5350"

        args = data.get("arguments") or []
        args_html = ""
        if args:
            items = "".join(
                f'<li style="margin-bottom:4px">{a.get("claim","")}'
                f'<br><span style="color:#9E9E9E;font-size:11px">{a.get("data_ref","")}</span></li>'
                for a in args
            )
            args_html = (
                f'<ul style="margin:8px 0 0 0;padding-left:18px;'
                f'font-size:12px;color:#555">{items}</ul>'
            )

        rebuttal_html = ""
        if data.get("rebuttal"):
            opp_lbl = "🐻 Bear 반박" if is_bull else "🐂 Bull 반박"
            rebuttal_html = (
                f'<div style="margin-top:8px;border-top:1px solid rgba(0,0,0,.08);padding-top:6px">'
                f'<div style="font-size:10px;font-weight:700;color:#9E9E9E;margin-bottom:2px">{opp_lbl}</div>'
                f'<div style="font-size:12px;color:#424242;line-height:1.6">{data["rebuttal"]}</div>'
                f'</div>'
            )

        body = (
            f'<div style="font-size:15px;color:#212121;line-height:1.7">{summary}</div>'
            f'<div style="margin-top:8px">'
            f'  <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:#757575">'
            f'    <span>confidence</span>'
            f'    <div style="flex:1;background:#E0E0E0;border-radius:4px;height:5px">'
            f'      <div style="background:{bar_col};width:{bar_w}%;height:100%;border-radius:4px"></div>'
            f'    </div>'
            f'    <span style="font-weight:700;color:{bar_col}">{conf:.2f}</span>'
            f'  </div>'
            f'</div>'
            f'{args_html}{rebuttal_html}'
        )

    return (
        f'<div style="display:flex;justify-content:{align};margin-bottom:16px">'
        f'  <div style="max-width:80%">'
        f'    <div style="font-size:11px;font-weight:700;color:{name_col};'
        f'                margin-bottom:4px;text-align:{name_align}">'
        f'      {label} &nbsp;·&nbsp; 라운드 {rnd}'
        f'    </div>'
        f'    <div style="background:{bg};border:1.5px solid {border};'
        f'                border-radius:{radius};padding:14px 16px;'
        f'                box-shadow:0 1px 4px rgba(0,0,0,.08)">'
        f'      {body}'
        f'    </div>'
        f'  </div>'
        f'</div>'
    )


def _agent_card_html(is_bull: bool, data: dict | None) -> str:
    emoji   = "🐂" if is_bull else "🐻"
    label   = "불 (Bull) 에이전트" if is_bull else "베어 (Bear) 에이전트"
    stance  = "낙관 관점" if is_bull else "비관 관점"
    accent  = "#4CAF50" if is_bull else "#EF5350"
    if not data or data.get("error"):
        body = (
            f'<div style="text-align:center;padding:28px 16px">'
            f'<div style="font-size:44px;margin-bottom:10px">{emoji}</div>'
            f'<div style="font-size:15px;font-weight:700;color:#111827;margin-bottom:6px">{label}</div>'
            f'<div style="font-size:13px;color:#9CA3AF;line-height:1.7;margin-bottom:14px">'
            f'LLM 연결 후 이 자리에<br>'
            f'<span style="color:{accent};font-weight:600">{stance}</span>의 토론 논거가 표시됩니다.</div>'
            f'<span style="display:inline-block;border:1px solid #E5E7EB;border-radius:20px;'
            f'padding:4px 14px;font-size:11px;color:#9CA3AF">연결 대기 중</span>'
            f'</div>'
        )
    else:
        conf = float(data.get("confidence") or 0)
        args_html = "".join(
            f'<li style="margin-bottom:3px;font-size:12px;color:#374151">{a.get("claim","")}'
            f'<br><span style="color:#9CA3AF;font-size:10px">{a.get("data_ref","")}</span></li>'
            for a in (data.get("arguments") or [])
        )
        rebuttal = data.get("rebuttal") or ""
        opponent_label = "🐻 Bear 논거에 대한 반박" if is_bull else "🐂 Bull 논거에 대한 반박"
        rebuttal_html = (
            f'<div style="margin-top:10px;padding-top:8px;border-top:1px solid #F3F4F6">'
            f'<div style="font-size:10px;font-weight:700;color:#9CA3AF;margin-bottom:3px">'
            f'{opponent_label}</div>'
            f'<div style="font-size:11px;color:#374151;line-height:1.6">{rebuttal}</div>'
            f'</div>'
        ) if rebuttal else ""
        body = (
            f'<div style="padding:16px">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'
            f'<span style="font-size:22px">{emoji}</span>'
            f'<span style="font-size:14px;font-weight:700;color:#111827">{label}</span>'
            f'<span style="margin-left:auto;font-size:13px;font-weight:700;color:{accent}">{conf:.2f}</span>'
            f'</div>'
            f'<div style="background:#F3F4F6;border-radius:4px;height:5px;margin-bottom:10px">'
            f'<div style="background:{accent};width:{int(conf*100)}%;height:100%;border-radius:4px"></div></div>'
            f'<div style="font-size:13px;color:#374151;line-height:1.7;margin-bottom:8px">'
            f'{data.get("summary","—")}</div>'
            f'<ul style="margin:0;padding-left:14px">{args_html}</ul>'
            f'{rebuttal_html}</div>'
        )
    return (
        f'<div style="border:1.5px dashed #E5E7EB;border-radius:14px;background:#fff;'
        f'min-height:200px">{body}</div>'
    )


def _verdict_card_html(state: dict | None) -> str:
    if not state:
        return (
            '<div style="border:1.5px dashed #E5E7EB;border-radius:14px;background:#fff">'
            '<div style="text-align:center;padding:28px 16px">'
            '<div style="font-size:44px;margin-bottom:10px">⚖️</div>'
            '<div style="font-size:15px;font-weight:700;color:#111827;margin-bottom:6px">오케스트레이터 최종 판정</div>'
            '<div style="font-size:13px;color:#9CA3AF;line-height:1.7;margin-bottom:14px">'
            '불/베어 에이전트 연결 후 이 자리에<br>'
            '합의 강도·판정 근거와 함께 최종 판정이 표시됩니다.</div>'
            '<span style="display:inline-block;border:1px solid #E5E7EB;border-radius:20px;'
            'padding:4px 14px;font-size:11px;color:#9CA3AF">연결 대기 중</span>'
            '</div></div>'
        )
    verdict      = state.get("verdict", "error")
    diff         = state.get("conf_diff", 0.0)
    bull_f       = state.get("bull_final") or {}
    bear_f       = state.get("bear_final") or {}
    orch_reason  = state.get("orch_reason", "")
    v_map = {
        "bullish": ("#059669", "🐂", "BULLISH"),
        "bearish": ("#DC2626", "🐻", "BEARISH"),
        "neutral": ("#D97706", "⚖️", "NEUTRAL"),
        "error":   ("#6B7280", "❌", "ERROR"),
    }
    v_color, v_icon, v_label = v_map.get(verdict, ("#6B7280", "?", verdict.upper()))
    bc   = float(bull_f.get("confidence") or 0)
    berc = float(bear_f.get("confidence") or 0)
    reason_html = (
        f'<div style="font-size:13px;color:#374151;line-height:1.75;'
        f'padding-top:12px;border-top:1px solid #F3F4F6">{orch_reason}</div>'
    ) if orch_reason else ""
    return (
        f'<div style="border:1.5px solid {v_color};border-radius:14px;background:#fff;padding:20px 24px">'
        f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;'
        f'color:#9CA3AF;margin-bottom:10px">⚖️ 최종 판정</div>'
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px">'
        f'<span style="font-size:26px;font-weight:900;color:{v_color}">{v_icon} {v_label}</span>'
        f'<span style="font-size:12px;color:#9CA3AF">차이 {diff:+.3f}</span></div>'
        f'<div style="display:flex;gap:20px;margin-bottom:12px">'
        f'<div style="flex:1"><div style="font-size:11px;color:#059669;font-weight:600;margin-bottom:4px">🐂 Bull {bc:.2f}</div>'
        f'<div style="background:#F3F4F6;border-radius:4px;height:5px">'
        f'<div style="background:#059669;width:{int(bc*100)}%;height:100%;border-radius:4px"></div></div></div>'
        f'<div style="flex:1"><div style="font-size:11px;color:#DC2626;font-weight:600;margin-bottom:4px">🐻 Bear {berc:.2f}</div>'
        f'<div style="background:#F3F4F6;border-radius:4px;height:5px">'
        f'<div style="background:#DC2626;width:{int(berc*100)}%;height:100%;border-radius:4px"></div></div></div>'
        f'</div>{reason_html}</div>'
    )


def _verdict_panel(bull_f: dict, bear_f: dict, verdict: str, diff: float) -> None:
    v_map = {
        "bullish": ("#059669", "🐂", "BULLISH"),
        "bearish": ("#DC2626", "🐻", "BEARISH"),
        "neutral": ("#D97706", "⚖️", "NEUTRAL"),
        "error":   ("#6B7280", "❌", "ERROR"),
    }
    v_color, v_icon, v_label = v_map.get(verdict, ("#6B7280", "?", verdict.upper()))
    bc   = float(bull_f.get("confidence") or 0)
    berc = float(bear_f.get("confidence") or 0)

    st.markdown(f"""
    <div style="background:#fff;border:1px solid #E5E7EB;border-radius:14px;
                padding:20px;border-top:3px solid {v_color};margin-bottom:12px">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                    letter-spacing:1px;color:#9CA3AF;margin-bottom:8px">⚖️ 최종 판정</div>
        <div style="font-size:26px;font-weight:900;color:{v_color}">{v_icon} {v_label}</div>
        <div style="font-size:12px;color:#6B7280;margin-top:4px">
            conf 차이: {diff:+.3f}
        </div>
        <hr style="border:none;border-top:1px solid #F3F4F6;margin:14px 0">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                    letter-spacing:.8px;color:#9CA3AF;margin-bottom:8px">Confidence</div>
        <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
            <span style="color:#059669">🐂 Bull</span>
            <span style="font-weight:700">{bc:.2f}</span>
        </div>
        <div style="background:#E5E7EB;border-radius:4px;height:6px;margin-bottom:10px">
            <div style="background:#059669;width:{bc*100:.0f}%;height:100%;border-radius:4px"></div>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
            <span style="color:#DC2626">🐻 Bear</span>
            <span style="font-weight:700">{berc:.2f}</span>
        </div>
        <div style="background:#E5E7EB;border-radius:4px;height:6px">
            <div style="background:#DC2626;width:{berc*100:.0f}%;height:100%;border-radius:4px"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════

session = load_session()

# support_data.json 직접 로드 (session_state 거치지 않음)
_support_cache = load_support_data()

def _generate_topic_and_support() -> None:
    """주제 생성 + 지원 데이터 수집을 한 번에 실행"""
    _debate_dir = os.path.join(ROOT, "debate")
    if _debate_dir not in sys.path:
        sys.path.insert(0, _debate_dir)
    try:
        from debate_topic_agent import run as _run_topic, save_session as _save_topic  # noqa: E402
        with st.status("📰 네이버 경제 헤드라인 분석 중...", expanded=True) as _s:
            st.write("헤드라인 크롤링 중...")
            _result = _run_topic()
            if _result:
                _save_topic(_result)
                st.write("✅ 주제 저장 완료.")
                _s.update(label="⚙️ 지원 데이터 수집 중...", state="running")

                _stock_d = _result.get("stock_debate") or {}
                _theme_d = _result.get("theme_debate") or {}
                _sup_data: dict = {}

                st.write("🏛️ Macro 에이전트 실행 중...")
                _sup_data["macro"] = _load_macro()
                st.write("🌡️ Sentiment 에이전트 실행 중...")
                _sup_data["market"] = _load_market()

                if _stock_d.get("ticker"):
                    st.write(f"🏭 종목 Sector ({_stock_d['ticker']}) 실행 중...")
                    _sup_data["stock_sector"] = _load_sector(
                        _stock_d["ticker"],
                        _stock_d.get("stock_name", ""),
                        _stock_d.get("sector_etf", ""),
                    )
                if _theme_d.get("sector_etf"):
                    st.write(f"🏭 테마 Sector ({_theme_d['sector_etf']}) 실행 중...")
                    _sup_data["theme_sector"] = _load_sector(
                        _theme_d["sector_etf"],
                        _theme_d.get("sector", "테마"),
                        _theme_d.get("sector_etf", ""),
                    )

                with open(SUPPORT_JSON, "w", encoding="utf-8") as _f:
                    json.dump(_sup_data, _f, ensure_ascii=False, indent=2)

                # 기존 토론 결과 초기화 (새 주제이므로)
                for _k in ("debate_stock", "debate_theme"):
                    st.session_state.pop(_k, None)

                _s.update(label="✅ 주제 및 데이터 생성 완료!", state="complete")
                st.rerun()
            else:
                _s.update(label="❌ 주제 생성 실패", state="error")
                st.error("헤드라인 수집 또는 GPT 분석에 실패했습니다. API 키와 네트워크 상태를 확인하세요.")
    except Exception as _e:
        st.error(f"오류: {_e}")


# ── 페이지 헤더 ───────────────────────────────────────────────
_hdr_left, _hdr_right = st.columns([4, 1])
with _hdr_left:
    st.markdown("""
    <div style="margin-bottom:1.5rem">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;
        letter-spacing:1.2px;color:#F97316;margin-bottom:6px">Daily Debate</div>
        <div style="font-size:28px;font-weight:900;color:#111827">토론 브리핑</div>
        <div style="font-size:14px;color:#6B7280;margin-top:6px">
            불(Bull) · 베어(Bear) 에이전트가 오늘의 핵심 뉴스로 토론하고 최종 판정을 내립니다.
        </div>
    </div>
    """, unsafe_allow_html=True)
with _hdr_right:
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    if st.button("📰 주제 재생성", key="regen_topic", use_container_width=True):
        _generate_topic_and_support()

if not _AGENTS_OK:
    callout(f"⚠️ 에이전트 임포트 실패: {_AGENTS_ERR}", kind="warn")

if not session:
    callout("📭 오늘의 토론 주제가 아직 생성되지 않았습니다.", kind="warn")
    if st.button("📰 오늘의 주제 생성하기", type="primary", key="gen_topic_first"):
        _generate_topic_and_support()
    st.stop()

stock_d = session.get("stock_debate") or {}
theme_d = session.get("theme_debate") or {}
created = session.get("created_at", "—")

tab_stock, tab_theme = st.tabs([
    f"📌 종목토론 — {stock_d.get('stock_name', '—')}",
    f"🌐 테마토론 — {theme_d.get('sector', '—')}",
])

for tab, debate in [(tab_stock, stock_d), (tab_theme, theme_d)]:
    with tab:
        if not debate:
            callout("이 탭의 토론 주제가 없습니다.", kind="warn")
            continue

        ticker    = debate.get("ticker")         # 테마토론이면 None
        etf       = debate.get("sector_etf", "")
        topic_txt = debate.get("debate_topic", "—")
        news      = debate.get("news") or {}
        d_type    = debate.get("debate_type", "stock")
        sector    = debate.get("sector", "—")
        sname     = debate.get("stock_name")
        state_key = f"debate_{d_type}"

        # ── 토론 주제 카드 ─────────────────────────────────────
        type_cls   = "type-stock" if d_type == "stock" else "type-theme"
        type_label = "종목토론 (Stock)" if d_type == "stock" else "테마토론 (Theme)"
        meta_parts = []
        if sname:   meta_parts.append(f"종목: {sname} ({ticker})")
        if sector:  meta_parts.append(f"섹터: {sector}")
        if etf:     meta_parts.append(f"ETF: {etf}")
        meta_str = "&nbsp;&nbsp;·&nbsp;&nbsp;".join(meta_parts)

        st.markdown(f"""
        <div class="debate-topic-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;
                        flex-wrap:wrap;gap:8px">
                <div class="debate-type-lbl {type_cls}">{type_label}</div>
                <div style="font-size:11px;color:#92400E">
                    생성: {created[:16] if created != "—" else "—"}
                </div>
            </div>
            <div class="debate-topic-text">{topic_txt}</div>
            <div class="debate-topic-meta">{meta_str}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── 뉴스 링크 ──────────────────────────────────────────
        if news.get("url") or news.get("title"):
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            nc1, nc2 = st.columns([4, 1])
            with nc1:
                press = news.get("press", "")
                pub   = (news.get("published_at") or "")[:16]
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
                        f'원문 보기 <span class="btn-arr">→</span></a></div>',
                        unsafe_allow_html=True,
                    )

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        st.divider()

        # ── 지원 에이전트 데이터 패널 ─────────────────────────────
        # support_data.json에서 직접 읽음 (session_state 불필요)
        _sec_key    = "stock_sector" if d_type == "stock" else "theme_sector"
        market_data = _support_cache.get("market")
        macro_data  = _support_cache.get("macro")
        sector_data = _support_cache.get(_sec_key)
        sec_title("입력 데이터 — 에이전트 분석 컨텍스트")

        dp1, dp2, dp3 = st.columns(3)

        with dp1:
            mkt_score = (market_data or {}).get("sentiment_score")
            mkt_label = (market_data or {}).get("sentiment_label", "—")
            vkospi_d  = (market_data or {}).get("vkospi") or {}
            vkospi    = vkospi_d.get("value") if isinstance(vkospi_d, dict) else None
            st.markdown(f"""
            <div class="support-panel">
                <div class="support-panel-title">🌡️ 시장 심리</div>
                <div class="support-kv">
                    <span class="support-key">심리 점수</span>
                    <span class="support-val {
                        'pos' if (mkt_score or 0) > 0.5
                        else 'neg' if (mkt_score or 0) < 0.3
                        else 'neu'
                    }">{f"{mkt_score:.2f}" if mkt_score is not None else "—"}</span>
                </div>
                <div class="support-kv">
                    <span class="support-key">심리 레이블</span>
                    <span class="support-val">{mkt_label}</span>
                </div>
                <div class="support-kv">
                    <span class="support-key">VKOSPI</span>
                    <span class="support-val {'neg' if (vkospi or 0) > 25 else 'pos'}">{
                        f"{vkospi:.1f}" if vkospi is not None else "—"
                    }</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with dp2:
            regime = "—"
            fsi    = "—"
            risk   = "—"
            if macro_data:
                probs  = (macro_data.get("quantitative_models") or {}).get("regime_probabilities") or {}
                p_n    = probs.get("state_0_normal", 0)
                p_c    = probs.get("state_1_caution", 0)
                p_k    = probs.get("state_2_crisis", 0)
                regime = "정상" if p_n >= .7 else ("주의" if p_c >= .5 else "위기" if p_k >= .5 else "혼조")
                fsi_v  = (macro_data.get("quantitative_models") or {}).get("fsi_factor_score")
                fsi    = f"{fsi_v:.3f}" if fsi_v is not None else "—"
                risk_raw = (macro_data.get("objective_analysis") or {}).get("risk_assessment", "")
                risk = (risk_raw.split("수준")[0].strip() + " 수준") if "수준" in risk_raw else risk_raw[:15]
            st.markdown(f"""
            <div class="support-panel">
                <div class="support-panel-title">🏛️ 매크로 국면</div>
                <div class="support-kv">
                    <span class="support-key">현재 국면</span>
                    <span class="support-val {
                        'pos' if regime == '정상' else 'neg' if regime == '위기' else 'neu'
                    }">{regime}</span>
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
                streak   = (sector_data.get("supply_demand") or {}).get("streak") or {}
                sd_trend = streak.get("institutional_5d_trend", "—")
                _per_raw = (sector_data.get("valuation") or {}).get("per_label") or "—"
                per_lbl  = {"역사적 저평가 구간 (하위 20%)": "저평가 (하위 20%)",
                            "역사적 고평가 구간 (상위 20%)": "고평가 (상위 20%)",
                            "역사적 중간 구간": "중간 구간"}.get(_per_raw, _per_raw)
                yoy_v    = ((sector_data.get("earnings") or {}).get("yoy") or {}).get("op_income_chg")
                yoy_op   = f"{yoy_v:+.1f}%" if yoy_v is not None else "—"
            st.markdown(f"""
            <div class="support-panel">
                <div class="support-panel-title">🏭 섹터 데이터</div>
                <div class="support-kv">
                    <span class="support-key">기관 5일 추세</span>
                    <span class="support-val {
                        'pos' if '매수' in str(sd_trend)
                        else 'neg' if '매도' in str(sd_trend)
                        else ''
                    }">{sd_trend}</span>
                </div>
                <div class="support-kv">
                    <span class="support-key">PER 위치</span>
                    <span class="support-val">{per_lbl}</span>
                </div>
                <div class="support-kv">
                    <span class="support-key">영업이익 YoY</span>
                    <span class="support-val {
                        'pos' if '+' in str(yoy_op) else 'neg' if yoy_op.startswith('-') else ''
                    }">{yoy_op}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        if not any([market_data, macro_data, sector_data]):
            callout(
                "📰 주제 재생성 버튼을 눌러 Macro · Sector · Sentiment 데이터를 수집하세요.",
                kind="orange",
            )

        st.divider()

        # ── 토론 컨트롤 ────────────────────────────────────────
        sec_title("에이전트 토론")

        rounds = 2
        do_debate = st.button(
            "🚀 토론 시작",
            key=f"start_{d_type}",
            type="primary",
            disabled=not _AGENTS_OK,
        )

        # ── 토론 실행 ───────────────────────────────────────────
        if do_debate:
            _ticker      = ticker or etf
            _ticker_name = sname or sector or "테마"
            _macro  = _support_cache.get("macro")
            _sector = _support_cache.get("stock_sector" if d_type == "stock" else "theme_sector")
            _market = _support_cache.get("market")

            with st.spinner("📦 입력 패키지 조립 중..."):
                pkg = build_input_package(
                    ticker=_ticker,
                    ticker_name=_ticker_name,
                    macro_payload=_macro,
                    sector_payload=_sector,
                    sentiment_payload=_market,
                    topic_type="종목" if d_type == "stock" else "테마",
                )

            # 에이전트 카드 — 라운드마다 업데이트
            _ca, _cb = st.columns(2)
            _bull_slot = _ca.empty()
            _bear_slot = _cb.empty()
            _bull_slot.markdown(_agent_card_html(True, None),  unsafe_allow_html=True)
            _bear_slot.markdown(_agent_card_html(False, None), unsafe_allow_html=True)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            # 판정 카드 슬롯
            _verdict_slot = st.empty()
            _verdict_slot.markdown(_verdict_card_html(None), unsafe_allow_html=True)

            st.divider()
            sec_title("💬 토론 대화 흐름")

            # 채팅 스트리밍 슬롯
            _chat_slot  = st.empty()
            _chat_parts = []
            msgs   = []
            bull_r = None
            bear_r = None

            for rnd in range(1, rounds + 1):
                with st.spinner(f"💬 라운드 {rnd}/{rounds} — 🐂 Bull 분석 중..."):
                    bull_r = _bull_fn(pkg, bear_r, MODEL)
                with st.spinner(f"💬 라운드 {rnd}/{rounds} — 🐻 Bear 분석 중..."):
                    bear_r = _bear_fn(pkg, bull_r, MODEL)

                msgs.extend([("bull", rnd, bull_r), ("bear", rnd, bear_r)])
                _chat_parts += [
                    _chat_bubble_html("bull", rnd, bull_r),
                    _chat_bubble_html("bear", rnd, bear_r),
                ]
                # 채팅 버블 즉시 반영
                _chat_slot.markdown(
                    '<div style="background:#FAFAFA;border:1px solid #E5E7EB;'
                    'border-radius:14px;padding:20px 16px">'
                    + "".join(_chat_parts) + "</div>",
                    unsafe_allow_html=True,
                )
                # 에이전트 카드 업데이트
                _bull_slot.markdown(_agent_card_html(True,  bull_r), unsafe_allow_html=True)
                _bear_slot.markdown(_agent_card_html(False, bear_r), unsafe_allow_html=True)

            verdict, diff = _classify(bull_r, bear_r)
            with st.spinner("⚖️ 판정 이유 생성 중..."):
                orch_reason = _run_orchestrator(bull_r, bear_r, verdict, diff)

            _final_state = {
                "messages":    msgs,
                "bull_final":  bull_r,
                "bear_final":  bear_r,
                "verdict":     verdict,
                "conf_diff":   diff,
                "orch_reason": orch_reason,
                "rounds":      rounds,
            }
            st.session_state[state_key] = _final_state
            _verdict_slot.markdown(_verdict_card_html(_final_state), unsafe_allow_html=True)
            st.caption(f"🤖 {MODEL}  |  {rounds}라운드")

        # ── 이전 결과 렌더링 ────────────────────────────────────
        elif st.session_state.get(state_key):
            ds = st.session_state[state_key]

            _ca, _cb = st.columns(2)
            with _ca:
                st.markdown(_agent_card_html(True,  ds.get("bull_final")), unsafe_allow_html=True)
            with _cb:
                st.markdown(_agent_card_html(False, ds.get("bear_final")), unsafe_allow_html=True)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown(_verdict_card_html(ds), unsafe_allow_html=True)

            st.divider()
            sec_title("💬 토론 대화 흐름")
            st.markdown(
                '<div style="background:#FAFAFA;border:1px solid #E5E7EB;'
                'border-radius:14px;padding:20px 16px">'
                + "".join(_chat_bubble_html(mt, r, d) for mt, r, d in ds["messages"])
                + "</div>",
                unsafe_allow_html=True,
            )
            st.caption(f"🤖 {MODEL}  |  {ds['rounds']}라운드")

        # ── 초기 placeholder ────────────────────────────────────
        else:
            _ca, _cb = st.columns(2)
            with _ca:
                st.markdown(_agent_card_html(True,  None), unsafe_allow_html=True)
            with _cb:
                st.markdown(_agent_card_html(False, None), unsafe_allow_html=True)
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown(_verdict_card_html(None), unsafe_allow_html=True)
