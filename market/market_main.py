# 전체 에이전트를 실행하는 메인 파일

import os
import sys
import subprocess
import json

def apply_pykrx_patch():
    """market_main.py 실행 전 pykrx 패치 스크립트를 자동 실행"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    patch_script_path = os.path.join(current_dir, "utils", "patch_pykrx.py")

    if not os.path.exists(patch_script_path):
        print(f"⚠️ 패치 파일을 찾을 수 없습니다: {patch_script_path}")
        return

    print("🔧 pykrx 환경을 점검합니다 (패치 스크립트 가동)...")
    result = subprocess.run([sys.executable, "-X", "utf8", patch_script_path], capture_output=True, text=True, encoding="utf-8", errors="replace")

    if result.returncode != 0:
        print("❌ pykrx 패치 중 문제가 발생했습니다:")
        print(result.stderr)
        sys.exit(1)
    else:
        print("✅ pykrx 패치 상태 점검 완료.\n")


# 1. 외부 모듈 import 전에 패치부터 먼저 실행
apply_pykrx_patch()

# 2. 패치 완료 후 필요한 모듈들 import
from dotenv import load_dotenv
from market_collectors.sentiment_collector import MarketSentimentCollector

if __name__ == "__main__":
    print("🚀 market agent 브리핑을 시작합니다...")

    # 환경변수 로드
    load_dotenv()

    # 데이터 수집 및 분석 실행
    collector = MarketSentimentCollector()
    final_json = collector.analyze_sentiment()
    
    # 터미널에 출력 (확인용)
    print("\n=== Market Sentiment Analysis Result ===")
    print(json.dumps(final_json, indent=2, ensure_ascii=False))

    # 파일로 저장 (다른 에이전트 전달용)
    # 현재 파일(market_main.py)을 기준으로 output 폴더 경로를 안전하게 자동 계산
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir) # 상위 폴더(multi-agent-trading)로 이동
    output_dir = os.path.join(project_root, "output")
    
    # 만약 output 폴더가 없다면 자동으로 생성
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "market_agent.json")
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_json, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 결과가 '{output_path}'에 성공적으로 저장되었습니다.")
    except Exception as e:
        print(f"\n❌ 파일 저장 실패: {e}")