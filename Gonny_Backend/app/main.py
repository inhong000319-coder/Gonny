"""FastAPI app entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.db.base import Base
from app.db.session import engine
from app.routers.context import router as context_router
from app.routers.itinerary import router as itinerary_router
from app.routers.admin_destinations import router as admin_destinations_router
from app.routers.rule_itinerary import router as rule_itinerary_router
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Gonny API"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(context_router, prefix=settings.api_prefix)
app.include_router(admin_destinations_router)
app.include_router(trip_router)
app.include_router(itinerary_router)
app.include_router(rule_itinerary_router)
