"""FastAPI app entrypoint."""

from __future__ import annotations

from fastapi import FastAPI

from app.core.settings import settings
from app.routers.context import router as context_router


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Travel context API for Gonny role-B owned features",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(context_router, prefix=settings.api_prefix)

