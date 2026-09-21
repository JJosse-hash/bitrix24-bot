from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from address_ai.bitrix.dashboard import router as bitrix_dashboard_router
from address_ai.bitrix.scanner import scanner
from address_ai.bitrix.webhook import router as bitrix_router

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("bitrix-bot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await scanner.start()
    try:
        yield
    finally:
        await scanner.stop()


app = FastAPI(title="Bitrix24 Bot", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bitrix_dashboard_router)
app.include_router(bitrix_router)


@app.get("/api/health")
def api_health() -> dict[str, str]:
    return {"status": "ok"}
