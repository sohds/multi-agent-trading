from __future__ import annotations

import uvicorn

from news_helper.config import load_env


def main() -> int:
    load_env()
    uvicorn.run("news_helper.web.app:app", host="127.0.0.1", port=8000, reload=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
