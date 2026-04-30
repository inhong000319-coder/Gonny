"""FastAPI app entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.core.settings import settings
from app.db.base import Base
from app.db.session import engine
from app.routers.context import router as context_router
from app.routers.itinerary import router as itinerary_router
from app.routers.admin_destinations import router as admin_destinations_router
from app.routers.community import feed_router as community_feed_router
from app.routers.community import router as community_router
from app.routers.rule_itinerary import router as rule_itinerary_router
from app.routers.trip import router as trip_router
import app.models.itinerary
import app.models.place_review
import app.models.trip
import app.models.travel_journal


UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if engine is not None:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(bind=engine)
        with engine.begin() as connection:
            inspector = inspect(connection)
            trip_columns = {column["name"] for column in inspector.get_columns("trips")} if "trips" in inspector.get_table_names() else set()
            if "title" not in trip_columns:
                connection.execute(text("ALTER TABLE trips ADD COLUMN title VARCHAR NOT NULL DEFAULT '새 여행'"))
            if "is_favorite" not in trip_columns:
                connection.execute(text("ALTER TABLE trips ADD COLUMN is_favorite BOOLEAN NOT NULL DEFAULT FALSE"))
            trip_todo_columns = {column["name"] for column in inspector.get_columns("trip_todos")} if "trip_todos" in inspector.get_table_names() else set()
            if "day_number" not in trip_todo_columns:
                connection.execute(text("ALTER TABLE trip_todos ADD COLUMN day_number INTEGER NOT NULL DEFAULT 1"))
            table_names = set(inspector.get_table_names())
            if "travel_journal_comment_reactions" not in table_names:
                connection.execute(
                    text(
                        """
                        CREATE TABLE travel_journal_comment_reactions (
                            id SERIAL PRIMARY KEY,
                            comment_id INTEGER NOT NULL REFERENCES travel_journal_comments(id),
                            reaction_type VARCHAR NOT NULL,
                            count INTEGER NOT NULL DEFAULT 0,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            CONSTRAINT uq_comment_reaction_type UNIQUE (comment_id, reaction_type)
                        )
                        """
                    )
                )
            if "place_review_reactions" not in table_names:
                connection.execute(
                    text(
                        """
                        CREATE TABLE place_review_reactions (
                            id SERIAL PRIMARY KEY,
                            review_id INTEGER NOT NULL REFERENCES place_reviews(id),
                            reaction_type VARCHAR NOT NULL,
                            count INTEGER NOT NULL DEFAULT 0,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            CONSTRAINT uq_place_review_reaction_type UNIQUE (review_id, reaction_type)
                        )
                        """
                    )
                )
            comment_columns = {column["name"] for column in inspector.get_columns("travel_journal_comments")} if "travel_journal_comments" in table_names else set()
            if "author_id" not in comment_columns:
                connection.execute(text("ALTER TABLE travel_journal_comments ADD COLUMN author_id VARCHAR"))
            if "author_name" not in comment_columns:
                connection.execute(text("ALTER TABLE travel_journal_comments ADD COLUMN author_name VARCHAR"))
            if "author_role" not in comment_columns:
                connection.execute(text("ALTER TABLE travel_journal_comments ADD COLUMN author_role VARCHAR"))
            journal_columns = {column["name"] for column in inspector.get_columns("travel_journals")} if "travel_journals" in table_names else set()
            if "view_count" not in journal_columns:
                connection.execute(text("ALTER TABLE travel_journals ADD COLUMN view_count INTEGER NOT NULL DEFAULT 0"))
            if "content_blocks" not in journal_columns:
                connection.execute(text("ALTER TABLE travel_journals ADD COLUMN content_blocks JSON NOT NULL DEFAULT '[]'::json"))
            if "image_urls" not in journal_columns:
                connection.execute(text("ALTER TABLE travel_journals ADD COLUMN image_urls JSON NOT NULL DEFAULT '[]'::json"))
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

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR, check_dir=False), name="uploads")


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
app.include_router(community_router)
app.include_router(community_feed_router)
app.include_router(rule_itinerary_router)
