from __future__ import annotations

import uvicorn

from src import config

if __name__ == "__main__":
    uvicorn.run(
        "src.api.app:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=False,
    )
