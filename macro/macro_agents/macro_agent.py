import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

from macro_collectors.ecos_api import get_macro_raw_data
from macro_collectors.quant_models import run_macro_quant_pipeline
from utils.logger import get_logger

load_dotenv(find_dotenv())
logger = get_logger("macro_agent")

def run_macro_agent() -> dict:
    as_of = datetime.now().strftime("%Y-%m-%d %H:%M")
    logger.info("=== 매크로 에이전트 시작 ===")
    
    payload = {
        "meta": {
            "as_of": as_of,
            "base_models": [
                "3-State Univariate Markov Regime Switching", 
                "PCA-based FSI Extraction", 
                "PCA Weight Decomposition"
            ]
        },
        "raw_indicators": None,
        "quantitative_models": None,
        "objective_analysis": None,
        "errors": []
    }
    
    try:
        logger.info("[1/2] 원천 데이터 수집 모듈 가동")
        df_merged = get_macro_raw_data()
        payload["meta"]["data_as_of"] = df_merged.index[-1].strftime("%Y-%m-%d")
        
        logger.info("[2/2] 퀀트 모델 파이프라인 가동")
        model_result = run_macro_quant_pipeline(df_merged)
        
        # 새로 개편된 JSON 구조 매핑
        payload["raw_indicators"] = model_result["raw_indicators"]
        payload["quantitative_models"] = model_result["quantitative_models"]
        payload["objective_analysis"] = model_result["objective_analysis"]

        # 수렴 실패 시 errors에 명시적으로 기록 (다운스트림 에이전트가 신뢰도를 판단할 수 있도록)
        if not model_result["quantitative_models"].get("markov_converged", True):
            payload["errors"].append(
                "마코프 국면전환 모형 수렴 실패: regime_probabilities 추정치가 불안정할 수 있습니다. "
                "해당 국면 확률 및 리스크 진단을 과신하지 마십시오."
            )
        
    except Exception as e:
        msg = f"에이전트 구동 중 오류 발생: {e}"
        logger.error(msg)
        payload["errors"].append(msg)

    logger.info(f"=== 매크로 에이전트 완료 (오류: {len(payload['errors'])}건) ===")
    return payload

def save_payload(payload: dict, output_dir: str = "output") -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"macro_agent_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    return path