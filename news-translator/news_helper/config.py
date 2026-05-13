import os
from pathlib import Path
from dotenv import load_dotenv

def load_env():
    """상위 폴더에 있는 .env 파일을 찾아 환경 변수를 로드합니다."""
    # 1. config.py 파일 위치 기준으로 3단계 위(multi-agent-trading)를 찾습니다.
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    
    # 2. .env 파일 경로 지정
    ENV_PATH = BASE_DIR / ".env"
    
    # 3. 로드 실행
    load_dotenv(dotenv_path=ENV_PATH)

# 다른 모듈에서 import 할 때 자동으로 한 번 실행되도록 추가
load_env()

def get_str_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)

def get_int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

def get_float_env(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default

def get_bool_env(key: str, default: bool = False) -> bool:
    val = os.getenv(key, str(default)).lower()
    return val in ("true", "1", "yes")