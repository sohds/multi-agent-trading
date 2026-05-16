import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent


def load_env() -> None:
    """Load env vars from the repo root and from news-translator."""
    load_dotenv(dotenv_path=REPO_ROOT / ".env", override=False)
    load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)


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
