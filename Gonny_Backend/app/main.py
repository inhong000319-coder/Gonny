"""FastAPI app entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.settings import settings
from app.db.base import Base
from app.db.session import engine
from app.routers.context import router as context_router
from app.routers.itinerary import router as itinerary_router
from app.routers.trip import router as trip_router
import app.models.itinerary
import app.models.trip


@asynccontextmanager
async def lifespan(app: FastAPI):
    if engine is not None:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Travel context API for Gonny role-B owned features",
    lifespan=lifespan,
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Gonny API"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(context_router, prefix=settings.api_prefix)
app.include_router(trip_router)
app.include_router(itinerary_router)
