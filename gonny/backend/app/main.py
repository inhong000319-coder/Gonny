from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.itinerary import router as itinerary_router
from app.api.trip import router as trip_router
from app.core.redis import redis_client
from app.db.base import Base
from app.db.session import SessionLocal, engine
import app.models.itinerary
import app.models.trip


@asynccontextmanager
async def lifespan(app: FastAPI):
    if engine is not None:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Gonny API", lifespan=lifespan)
app.include_router(trip_router)
app.include_router(itinerary_router)


@app.get("/")
def read_root():
    return {"message": "Gonny API"}


@app.get("/health")
def health_check():
    db_status = "error"
    redis_status = "error"

    if SessionLocal is not None:
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception:
            db_status = "error"

    if redis_client is not None:
        try:
            redis_client.ping()
            redis_status = "ok"
        except Exception:
            redis_status = "error"

    return {
        "api": "ok",
        "db": db_status,
        "redis": redis_status,
    }
