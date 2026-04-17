import os
import sys
import json
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())
sys.path.insert(0, os.path.dirname(__file__))

from macro_agents.macro_agent import run_macro_agent, save_payload
from utils.logger import get_logger

logger = get_logger("main")

OUTPUT_DIR  = os.getenv("OUTPUT_DIR", "output")
SAVE_JSON   = os.getenv("SAVE_JSON", "true").lower() == "true"

SEP  = "=" * 62
SEP2 = "-" * 62

def h1(title: str): print(f"\n{SEP}\n  {title}\n{SEP}")
def h2(title: str): print(f"\n{SEP2}\n  ▸ {title}\n{SEP2}")

def main():
    payload = run_macro_agent()

    h1(f"매크로 에이전트 분석 결과 — {payload['meta']['as_of']}")
    
    # [수정] payload["raw_indicators"] 부분은 이미 맞게 되어있으므로 그대로 유지하거나 확인
    if payload.get("raw_indicators"):
        h2("1. 핵심 거시 지표 (4대 부문)")
        print(json.dumps(payload["raw_indicators"], indent=2, ensure_ascii=False))

    # [수정] 키 이름 유지 
    if payload.get("objective_analysis"):
        h2("2. 마코프 국면전환 및 PCA 원인 분석")
        diag = payload["objective_analysis"]
        print(f"  국면 진단 : {diag.get('current_regime_diagnosis')}")
        print(f"  위험도    : {diag.get('risk_assessment')}")
        print(f"  모멘텀    : {diag.get('momentum')}")
        print(f"  XAI    : {diag.get('xai_reasoning')}")

    if payload["errors"]:
        h2("⚠️ 수집/연산 오류 목록")
        for i, e in enumerate(payload["errors"], 1):
            print(f"  {i}. {e}")

    if SAVE_JSON:
        saved_path = save_payload(payload, OUTPUT_DIR)
        print(f"\n  💾 JSON 저장 완료: {saved_path}")

    print(f"\n{SEP}\n")

if __name__ == "__main__":
    main()