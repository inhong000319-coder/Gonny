from pathlib import Path
from uuid import uuid4
import shutil

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.place_review import PlaceReview, PlaceReviewReaction, PlaceStat
from app.models.travel_journal import (
    TravelJournal,
    TravelJournalComment,
    TravelJournalCommentReaction,
    TravelJournalReaction,
    TravelJournalTodo,
    TripTodo,
)
from app.models.trip import Trip
from app.schemas.community import (
    CommunityFeedJournalResponse,
    CommunityFeedJournalListResponse,
    CommunityJournalDetailResponse,
    CommunityPlaceCardResponse,
    CommunityPlaceCityResponse,
    CommunityPlaceDetailResponse,
    CommunityPlaceListResponse,
    CommunityPlaceReviewItemResponse,
    CommunityFeedResponse,
    CommunityFeedReviewResponse,
    JournalImageUploadResponse,
    PlaceReviewCreate,
    PlaceReviewReactionCreate,
    PlaceReviewReactionResponse,
    PlaceReviewResponse,
    PlaceSuggestionResponse,
    PlaceReviewUpdate,
    TagSuggestionResponse,
    TripTodoCreate,
    TripTodoResponse,
    TripTodoUpdate,
    TravelJournalCommentCreate,
    TravelJournalCommentReactionCreate,
    TravelJournalCommentReactionResponse,
    TravelJournalCommentResponse,
    TravelJournalCommentUpdate,
    TravelJournalCreate,
    TravelJournalReactionCreate,
    TravelJournalReactionResponse,
    TravelJournalUpdate,
    TravelJournalResponse,
    TripCommunityResponse,
)
from app.services.place_review_stats_service import refresh_place_stat


router = APIRouter(prefix="/trips/{trip_id}", tags=["trip-community"])
feed_router = APIRouter(tags=["community-feed"])
UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"


def build_recommendation_count(reactions: list[TravelJournalReaction]) -> int:
    return sum(max(reaction.count, 0) for reaction in reactions)


def normalize_travel_journal_content_blocks(
    content_blocks: list[dict] | list | None,
    diary_text: str,
    image_urls: list[str] | None,
) -> list[dict]:
    normalized_blocks: list[dict] = []
    raw_blocks = content_blocks or []
    for index, raw_block in enumerate(raw_blocks):
        block_data = raw_block if isinstance(raw_block, dict) else raw_block.model_dump()
        block_type = block_data.get("type")
        block_id = block_data.get("id") or f"block-{index + 1}"
        if block_type == "text":
            text_value = (block_data.get("text") or "").strip()
            if not text_value:
                continue
            normalized_blocks.append(
                {
                    "id": block_id,
                    "type": "text",
                    "text": text_value,
                }
            )
        elif block_type == "image":
            image_url = (block_data.get("url") or "").strip()
            if not image_url:
                continue
            overlay_text = (block_data.get("overlay_text") or "").strip()
            emoji_value = (block_data.get("emoji") or "").strip()
            text_items = block_data.get("text_items") or []
            emoji_items = block_data.get("emoji_items") or []
            draw_items = block_data.get("draw_items") or []
            if overlay_text and not text_items:
                text_items = [{"id": f"{block_id}-text-1", "text": overlay_text, "x": 50, "y": 82}]
            if emoji_value and not emoji_items:
                emoji_items = [{"id": f"{block_id}-emoji-1", "emoji": emoji_value, "x": 84, "y": 18, "size": 42}]
            normalized_blocks.append(
                {
                    "id": block_id,
                    "type": "image",
                    "url": image_url,
                    "caption": (block_data.get("caption") or "").strip() or None,
                    "layout": block_data.get("layout") or "large",
                    "aspect_ratio": block_data.get("aspect_ratio") or "landscape",
                    "overlay_text": overlay_text or None,
                    "emoji": emoji_value or None,
                    "crop_x": max(0, min(100, int(block_data.get("crop_x", 50) or 50))),
                    "crop_y": max(0, min(100, int(block_data.get("crop_y", 50) or 50))),
                    "crop_left": max(0.0, min(99.0, float(block_data.get("crop_left", 0.0) or 0.0))),
                    "crop_top": max(0.0, min(99.0, float(block_data.get("crop_top", 0.0) or 0.0))),
                    "crop_width": max(1.0, min(100.0, float(block_data.get("crop_width", 100.0) or 100.0))),
                    "crop_height": max(1.0, min(100.0, float(block_data.get("crop_height", 100.0) or 100.0))),
                    "width_percent": max(30, min(100, int(block_data.get("width_percent", 100) or 100))),
                    "zoom": max(1.0, min(4.0, float(block_data.get("zoom", 1.0) or 1.0))),
                    "offset_x": max(-100.0, min(100.0, float(block_data.get("offset_x", 0.0) or 0.0))),
                    "offset_y": max(-100.0, min(100.0, float(block_data.get("offset_y", 0.0) or 0.0))),
                    "text_items": [item for item in text_items if isinstance(item, dict)],
                    "emoji_items": [item for item in emoji_items if isinstance(item, dict)],
                    "draw_items": [item for item in draw_items if isinstance(item, dict)],
                }
            )

    if normalized_blocks:
        return normalized_blocks

    fallback_blocks: list[dict] = []
    if diary_text.strip():
        fallback_blocks.append(
            {
                "id": "block-text-1",
                "type": "text",
                "text": diary_text.strip(),
            }
        )
    for index, image_url in enumerate(image_urls or [], start=1):
        if not image_url:
            continue
        fallback_blocks.append(
            {
                "id": f"block-image-{index}",
                "type": "image",
                "url": image_url,
                "caption": None,
                "layout": "large",
                "aspect_ratio": "landscape",
                "overlay_text": None,
                "emoji": None,
                "crop_x": 50,
                "crop_y": 50,
                "crop_left": 0.0,
                "crop_top": 0.0,
                "crop_width": 100.0,
                "crop_height": 100.0,
                "width_percent": 100,
                "zoom": 1.0,
                "offset_x": 0.0,
                "offset_y": 0.0,
                "text_items": [],
                "emoji_items": [],
                "draw_items": [],
            }
        )
    return fallback_blocks


def build_travel_journal_summary(content_blocks: list[dict], fallback_text: str) -> str:
    text_fragments = [(block.get("text") or "").strip() for block in content_blocks if block.get("type") == "text"]
    summary_source = "\n\n".join(fragment for fragment in text_fragments if fragment).strip() or fallback_text.strip()
    if len(summary_source) <= 600:
        return summary_source
    return f"{summary_source[:597].rstrip()}..."


def collect_travel_journal_image_urls(content_blocks: list[dict], fallback_urls: list[str] | None) -> list[str]:
    urls = [(block.get("url") or "").strip() for block in content_blocks if block.get("type") == "image"]
    normalized_urls = [url for url in urls if url]
    return normalized_urls or [url for url in (fallback_urls or []) if url]


def get_trip_or_404(trip_id: int, db: Session) -> Trip:
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip


def resolve_actor(
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    user_name: str | None = Header(default=None, alias="X-User-Name"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    return {
        "user_id": user_id.strip() if user_id else None,
        "user_name": user_name.strip() if user_name else None,
        "user_role": user_role.strip().lower() if user_role else None,
    }


def can_edit_comment(actor: dict[str, str | None], comment: TravelJournalComment) -> bool:
    if not actor.get("user_id") or not comment.author_id:
        return True
    return actor["user_id"] == comment.author_id


def can_delete_comment(actor: dict[str, str | None], comment: TravelJournalComment) -> bool:
    if not actor.get("user_id") or not comment.author_id:
        return True
    return actor["user_id"] == comment.author_id or actor.get("user_role") == "admin"


@router.get("/community", response_model=TripCommunityResponse)
def get_trip_community(trip_id: int, db: Session = Depends(get_db)):
    get_trip_or_404(trip_id, db)

    trip_todos = (
        db.query(TripTodo)
        .filter(TripTodo.trip_id == trip_id)
        .order_by(TripTodo.day_number.asc(), TripTodo.sort_order.asc(), TripTodo.id.asc())
        .all()
    )
    journals = (
        db.query(TravelJournal)
        .options(
            selectinload(TravelJournal.todos),
            selectinload(TravelJournal.comments).selectinload(TravelJournalComment.reactions),
            selectinload(TravelJournal.reactions),
        )
        .filter(TravelJournal.trip_id == trip_id)
        .order_by(TravelJournal.created_at.desc(), TravelJournal.id.desc())
        .all()
    )
    reviews = (
        db.query(PlaceReview)
        .options(selectinload(PlaceReview.reactions))
        .filter(PlaceReview.trip_id == trip_id)
        .order_by(PlaceReview.created_at.desc(), PlaceReview.id.desc())
        .all()
    )
    stat_keys = {(review.city, review.place_name) for review in reviews}
    place_stats = [
        stat
        for city, place_name in stat_keys
        for stat in [db.query(PlaceStat).filter(PlaceStat.city == city, PlaceStat.place_name == place_name).first()]
        if stat is not None
    ]
    place_stats.sort(key=lambda stat: (-stat.review_count, -stat.average_rating, stat.place_name))

    return TripCommunityResponse(trip_todos=trip_todos, journals=journals, reviews=reviews, place_stats=place_stats)


@router.post("/community/journal-images", response_model=JournalImageUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_travel_journal_image(
    trip_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    content_type = image.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image uploads are supported")

    suffix = Path(image.filename or "image").suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = ".jpg"

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"journal-{trip_id}-{uuid4().hex}{suffix}"
    destination = UPLOADS_DIR / filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    return JournalImageUploadResponse(url=f"/uploads/{filename}")


@router.post("/community/todos", response_model=TripTodoResponse, status_code=status.HTTP_201_CREATED)
def create_trip_todo(
    trip_id: int,
    todo: TripTodoCreate,
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    next_order = (
        db.query(TripTodo)
        .filter(TripTodo.trip_id == trip_id, TripTodo.day_number == todo.day_number)
        .count()
    )
    db_todo = TripTodo(
        trip_id=trip_id,
        content=todo.content,
        day_number=todo.day_number,
        is_done=todo.is_done,
        sort_order=next_order,
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo


@router.patch("/community/todos/{todo_id}", response_model=TripTodoResponse)
def update_trip_todo(
    trip_id: int,
    todo_id: int,
    payload: TripTodoUpdate,
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    todo = db.query(TripTodo).filter(TripTodo.id == todo_id, TripTodo.trip_id == trip_id).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip todo not found")

    if payload.content is not None:
        todo.content = payload.content
    if payload.day_number is not None:
        todo.day_number = payload.day_number
    if payload.is_done is not None:
        todo.is_done = payload.is_done

    db.commit()
    db.refresh(todo)
    return todo


@router.post("/community/journals", response_model=TravelJournalResponse, status_code=status.HTTP_201_CREATED)
def create_travel_journal(
    trip_id: int,
    journal: TravelJournalCreate,
    db: Session = Depends(get_db),
):
    trip = get_trip_or_404(trip_id, db)
    normalized_blocks = normalize_travel_journal_content_blocks(journal.content_blocks, journal.diary_text, journal.image_urls)
    image_urls = collect_travel_journal_image_urls(normalized_blocks, journal.image_urls)
    if len(image_urls) > 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can upload up to 20 images")

    db_journal = TravelJournal(
        trip_id=trip_id,
        title=journal.title,
        diary_text=build_travel_journal_summary(normalized_blocks, journal.diary_text),
        reflection_text=journal.reflection_text,
        content_blocks=normalized_blocks,
        image_urls=image_urls,
        overall_rating=journal.overall_rating,
        share_with_community=journal.share_with_community,
    )
    trip.travel_journals.append(db_journal)
    db.commit()
    db.refresh(db_journal)
    return db_journal


@router.patch("/community/journals/{journal_id}", response_model=TravelJournalResponse)
def update_travel_journal(
    trip_id: int,
    journal_id: int,
    payload: TravelJournalUpdate,
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    journal = (
        db.query(TravelJournal)
        .options(
            selectinload(TravelJournal.todos),
            selectinload(TravelJournal.comments),
            selectinload(TravelJournal.reactions),
        )
        .filter(TravelJournal.id == journal_id, TravelJournal.trip_id == trip_id)
        .first()
    )
    if journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel journal not found")

    if payload.title is not None:
        journal.title = payload.title
    normalized_blocks = normalize_travel_journal_content_blocks(
        payload.content_blocks if payload.content_blocks is not None else journal.content_blocks,
        payload.diary_text if payload.diary_text is not None else journal.diary_text,
        payload.image_urls if payload.image_urls is not None else journal.image_urls,
    )
    image_urls = collect_travel_journal_image_urls(
        normalized_blocks,
        payload.image_urls if payload.image_urls is not None else journal.image_urls,
    )
    if len(image_urls) > 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can upload up to 20 images")
    if payload.diary_text is not None or payload.content_blocks is not None:
        journal.diary_text = build_travel_journal_summary(
            normalized_blocks,
            payload.diary_text if payload.diary_text is not None else journal.diary_text,
        )
    if payload.reflection_text is not None:
        journal.reflection_text = payload.reflection_text
    if payload.content_blocks is not None:
        journal.content_blocks = normalized_blocks
    if payload.image_urls is not None or payload.content_blocks is not None:
        journal.image_urls = image_urls
    if payload.overall_rating is not None:
        journal.overall_rating = payload.overall_rating
    if payload.share_with_community is not None:
        journal.share_with_community = payload.share_with_community

    db.commit()
    db.refresh(journal)
    return journal


@router.delete("/community/journals/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_travel_journal(
    trip_id: int,
    journal_id: int,
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    journal = db.query(TravelJournal).filter(TravelJournal.id == journal_id, TravelJournal.trip_id == trip_id).first()
    if journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel journal not found")

    db.delete(journal)
    db.commit()


@router.post("/community/journals/{journal_id}/comments", response_model=TravelJournalCommentResponse, status_code=status.HTTP_201_CREATED)
def create_travel_journal_comment(
    trip_id: int,
    journal_id: int,
    payload: TravelJournalCommentCreate,
    actor: dict[str, str | None] = Depends(resolve_actor),
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    journal = db.query(TravelJournal).filter(TravelJournal.id == journal_id, TravelJournal.trip_id == trip_id).first()
    if journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel journal not found")

    comment = TravelJournalComment(
        journal_id=journal_id,
        content=payload.content.strip(),
        author_id=actor.get("user_id"),
        author_name=actor.get("user_name"),
        author_role=actor.get("user_role"),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.patch("/community/journals/{journal_id}/comments/{comment_id}", response_model=TravelJournalCommentResponse)
def update_travel_journal_comment(
    trip_id: int,
    journal_id: int,
    comment_id: int,
    payload: TravelJournalCommentUpdate,
    actor: dict[str, str | None] = Depends(resolve_actor),
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    comment = (
        db.query(TravelJournalComment)
        .join(TravelJournal, TravelJournal.id == TravelJournalComment.journal_id)
        .filter(
            TravelJournalComment.id == comment_id,
            TravelJournalComment.journal_id == journal_id,
            TravelJournal.trip_id == trip_id,
        )
        .first()
    )
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel journal comment not found")
    if not can_edit_comment(actor, comment):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the author can edit this comment")

    comment.content = payload.content.strip()
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/community/journals/{journal_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_travel_journal_comment(
    trip_id: int,
    journal_id: int,
    comment_id: int,
    actor: dict[str, str | None] = Depends(resolve_actor),
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    comment = (
        db.query(TravelJournalComment)
        .join(TravelJournal, TravelJournal.id == TravelJournalComment.journal_id)
        .filter(
            TravelJournalComment.id == comment_id,
            TravelJournalComment.journal_id == journal_id,
            TravelJournal.trip_id == trip_id,
        )
        .first()
    )
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel journal comment not found")
    if not can_delete_comment(actor, comment):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the author or an admin can delete this comment")

    db.delete(comment)
    db.commit()


@router.post(
    "/community/journals/{journal_id}/comments/{comment_id}/reactions",
    response_model=TravelJournalCommentReactionResponse | None,
    status_code=status.HTTP_201_CREATED,
)
def create_travel_journal_comment_reaction(
    trip_id: int,
    journal_id: int,
    comment_id: int,
    payload: TravelJournalCommentReactionCreate,
    response: Response,
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    comment = (
        db.query(TravelJournalComment)
        .join(TravelJournal, TravelJournal.id == TravelJournalComment.journal_id)
        .filter(
            TravelJournalComment.id == comment_id,
            TravelJournalComment.journal_id == journal_id,
            TravelJournal.trip_id == trip_id,
        )
        .first()
    )
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel journal comment not found")

    reaction_type = payload.reaction_type.strip()
    delta = 1 if payload.delta >= 0 else -1
    reaction = (
        db.query(TravelJournalCommentReaction)
        .filter(
            TravelJournalCommentReaction.comment_id == comment_id,
            TravelJournalCommentReaction.reaction_type == reaction_type,
        )
        .first()
    )
    if reaction is None and delta < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reaction count cannot go below zero")

    if reaction is None:
        reaction = TravelJournalCommentReaction(comment_id=comment_id, reaction_type=reaction_type, count=1)
        db.add(reaction)
        db.commit()
        db.refresh(reaction)
        return reaction

    reaction.count = max(0, reaction.count + delta)
    if reaction.count == 0:
        db.delete(reaction)
        db.commit()
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    db.commit()
    db.refresh(reaction)
    return reaction


@router.post("/community/journals/{journal_id}/reactions", response_model=TravelJournalReactionResponse, status_code=status.HTTP_201_CREATED)
def create_travel_journal_reaction(
    trip_id: int,
    journal_id: int,
    payload: TravelJournalReactionCreate,
    response: Response,
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    journal = db.query(TravelJournal).filter(TravelJournal.id == journal_id, TravelJournal.trip_id == trip_id).first()
    if journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel journal not found")

    reaction_type = payload.reaction_type.strip()
    delta = 1 if payload.delta >= 0 else -1
    reaction = (
        db.query(TravelJournalReaction)
        .filter(TravelJournalReaction.journal_id == journal_id, TravelJournalReaction.reaction_type == reaction_type)
        .first()
    )
    if reaction is None and delta < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reaction count cannot go below zero")

    if reaction is None:
        reaction = TravelJournalReaction(journal_id=journal_id, reaction_type=reaction_type, count=1)
        db.add(reaction)
        db.commit()
        db.refresh(reaction)
        return reaction

    reaction.count = max(0, reaction.count + delta)
    if reaction.count == 0:
        db.delete(reaction)
        db.commit()
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    db.commit()
    db.refresh(reaction)
    return reaction


@router.post("/community/reviews", response_model=PlaceReviewResponse, status_code=status.HTTP_201_CREATED)
def create_place_review(
    trip_id: int,
    review: PlaceReviewCreate,
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    if review.journal_id is not None:
        journal = db.query(TravelJournal).filter(TravelJournal.id == review.journal_id, TravelJournal.trip_id == trip_id).first()
        if journal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel journal not found")

    db_review = PlaceReview(
        trip_id=trip_id,
        journal_id=review.journal_id,
        city=review.city.strip().lower(),
        place_id=review.place_id,
        place_name=review.place_name.strip(),
        rating=review.rating,
        visit_time_slot=review.visit_time_slot,
        companion_type=review.companion_type,
        recommended=review.recommended,
        would_revisit=review.would_revisit,
        tags=[tag.strip() for tag in review.tags if tag.strip()],
        review_text=review.review_text,
    )
    db.add(db_review)
    db.flush()
    refresh_place_stat(db=db, city=db_review.city, place_name=db_review.place_name)
    db.commit()
    db.refresh(db_review)
    return db_review


@router.patch("/community/reviews/{review_id}", response_model=PlaceReviewResponse)
def update_place_review(
    trip_id: int,
    review_id: int,
    payload: PlaceReviewUpdate,
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    review = db.query(PlaceReview).filter(PlaceReview.id == review_id, PlaceReview.trip_id == trip_id).first()
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place review not found")

    original_city = review.city
    original_place_name = review.place_name

    if payload.city is not None:
        review.city = payload.city.strip().lower()
    if payload.place_name is not None:
        review.place_name = payload.place_name.strip()
    if payload.place_id is not None:
        review.place_id = payload.place_id
    if payload.rating is not None:
        review.rating = payload.rating
    if payload.visit_time_slot is not None:
        review.visit_time_slot = payload.visit_time_slot
    if payload.companion_type is not None:
        review.companion_type = payload.companion_type
    if payload.recommended is not None:
        review.recommended = payload.recommended
    if payload.would_revisit is not None:
        review.would_revisit = payload.would_revisit
    if payload.tags is not None:
        review.tags = [tag.strip() for tag in payload.tags if tag.strip()]
    if payload.review_text is not None:
        review.review_text = payload.review_text

    db.flush()
    refresh_place_stat(db=db, city=review.city, place_name=review.place_name)
    if original_city != review.city or original_place_name != review.place_name:
        refresh_place_stat(db=db, city=original_city, place_name=original_place_name)
    db.commit()
    db.refresh(review)
    return review


@router.delete("/community/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_place_review(
    trip_id: int,
    review_id: int,
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    review = db.query(PlaceReview).filter(PlaceReview.id == review_id, PlaceReview.trip_id == trip_id).first()
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place review not found")

    original_city = review.city
    original_place_name = review.place_name
    db.delete(review)
    db.flush()
    refresh_place_stat(db=db, city=original_city, place_name=original_place_name)
    db.commit()


@router.post(
    "/community/reviews/{review_id}/reactions",
    response_model=PlaceReviewReactionResponse | None,
    status_code=status.HTTP_201_CREATED,
)
def create_place_review_reaction(
    trip_id: int,
    review_id: int,
    payload: PlaceReviewReactionCreate,
    response: Response,
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)
    review = db.query(PlaceReview).filter(PlaceReview.id == review_id, PlaceReview.trip_id == trip_id).first()
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place review not found")

    reaction_type = payload.reaction_type.strip()
    delta = 1 if payload.delta >= 0 else -1
    reaction = (
        db.query(PlaceReviewReaction)
        .filter(PlaceReviewReaction.review_id == review_id, PlaceReviewReaction.reaction_type == reaction_type)
        .first()
    )
    if reaction is None and delta < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reaction count cannot go below zero")

    if reaction is None:
        reaction = PlaceReviewReaction(review_id=review_id, reaction_type=reaction_type, count=1)
        db.add(reaction)
        db.commit()
        db.refresh(reaction)
        return reaction

    reaction.count = max(0, reaction.count + delta)
    if reaction.count == 0:
        db.delete(reaction)
        db.commit()
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    db.commit()
    db.refresh(reaction)
    return reaction


@router.get("/community/place-suggestions", response_model=list[PlaceSuggestionResponse])
def get_place_suggestions(
    trip_id: int,
    q: str = Query(min_length=1, max_length=60),
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)

    normalized = q.strip().lower()
    if not normalized:
        return []

    rows = (
        db.query(
            PlaceReview.place_name.label("place_name"),
            func.min(PlaceReview.city).label("city"),
            func.count(PlaceReview.id).label("review_count"),
            func.avg(PlaceReview.rating).label("average_rating"),
        )
        .filter(func.lower(PlaceReview.place_name).like(f"{normalized}%"))
        .group_by(PlaceReview.place_name)
        .order_by(func.count(PlaceReview.id).desc(), func.avg(PlaceReview.rating).desc(), PlaceReview.place_name.asc())
        .limit(limit)
        .all()
    )

    return [
        PlaceSuggestionResponse(
            place_name=row.place_name,
            city=row.city,
            review_count=int(row.review_count or 0),
            average_rating=float(row.average_rating) if row.average_rating is not None else None,
        )
        for row in rows
    ]


@router.get("/community/tag-suggestions", response_model=list[TagSuggestionResponse])
def get_tag_suggestions(
    trip_id: int,
    q: str = Query(min_length=1, max_length=40),
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    get_trip_or_404(trip_id, db)

    normalized = q.strip().lower()
    if not normalized:
        return []

    tag_counts: dict[str, int] = {}
    reviews = db.query(PlaceReview.tags).filter(PlaceReview.tags.isnot(None)).all()
    for (review_tags,) in reviews:
        if not review_tags:
            continue
        for tag in review_tags:
            cleaned = str(tag).strip()
            if cleaned and cleaned.lower().startswith(normalized):
                tag_counts[cleaned] = tag_counts.get(cleaned, 0) + 1

    return [
        TagSuggestionResponse(tag=tag, count=count)
        for tag, count in sorted(tag_counts.items(), key=lambda item: (item[0], -item[1]))[:limit]
    ]


@feed_router.get("/community-feed", response_model=CommunityFeedResponse)
def get_community_feed(
    limit: int = Query(default=24, ge=1, le=100),
    db: Session = Depends(get_db),
):
    journals = (
        db.query(TravelJournal, Trip)
        .join(Trip, Trip.id == TravelJournal.trip_id)
        .options(selectinload(TravelJournal.reactions))
        .filter(TravelJournal.share_with_community.is_(True))
        .order_by(TravelJournal.created_at.desc(), TravelJournal.id.desc())
        .limit(limit)
        .all()
    )
    reviews = (
        db.query(PlaceReview, Trip)
        .join(Trip, Trip.id == PlaceReview.trip_id)
        .order_by(PlaceReview.created_at.desc(), PlaceReview.id.desc())
        .limit(limit)
        .all()
    )

    return CommunityFeedResponse(
        journals=[
            CommunityFeedJournalResponse(
                id=journal.id,
                trip_id=trip.id,
                trip_title=trip.title,
                destination=trip.destination,
                title=journal.title,
                diary_text=journal.diary_text,
                reflection_text=journal.reflection_text,
                content_blocks=normalize_travel_journal_content_blocks(
                    journal.content_blocks,
                    journal.diary_text,
                    journal.image_urls,
                ),
                image_urls=collect_travel_journal_image_urls(
                    normalize_travel_journal_content_blocks(journal.content_blocks, journal.diary_text, journal.image_urls),
                    journal.image_urls,
                ),
                overall_rating=journal.overall_rating,
                view_count=journal.view_count,
                recommendation_count=build_recommendation_count(journal.reactions),
                created_at=journal.created_at,
                reactions=journal.reactions,
            )
            for journal, trip in journals
        ],
        reviews=[
            CommunityFeedReviewResponse(
                id=review.id,
                trip_id=trip.id,
                trip_title=trip.title,
                destination=trip.destination,
                city=review.city,
                place_name=review.place_name,
                rating=review.rating,
                visit_time_slot=review.visit_time_slot,
                companion_type=review.companion_type,
                recommended=review.recommended,
                would_revisit=review.would_revisit,
                tags=review.tags,
                review_text=review.review_text,
                created_at=review.created_at,
            )
            for review, trip in reviews
        ],
    )


@feed_router.get("/community-feed/journals", response_model=CommunityFeedJournalListResponse)
def get_community_feed_journals(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=30),
    sort: str = Query(default="views"),
    q: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    journal_rows = (
        db.query(TravelJournal, Trip)
        .join(Trip, Trip.id == TravelJournal.trip_id)
        .options(selectinload(TravelJournal.reactions))
        .filter(TravelJournal.share_with_community.is_(True))
        .all()
    )

    items = []
    keyword = q.strip().lower() if q else None
    for journal, trip in journal_rows:
        if keyword and keyword not in journal.title.lower():
            continue
        items.append(
            CommunityFeedJournalResponse(
                id=journal.id,
                trip_id=trip.id,
                trip_title=trip.title,
                destination=trip.destination,
                title=journal.title,
                diary_text=journal.diary_text,
                reflection_text=journal.reflection_text,
                content_blocks=normalize_travel_journal_content_blocks(
                    journal.content_blocks,
                    journal.diary_text,
                    journal.image_urls,
                ),
                image_urls=collect_travel_journal_image_urls(
                    normalize_travel_journal_content_blocks(journal.content_blocks, journal.diary_text, journal.image_urls),
                    journal.image_urls,
                ),
                overall_rating=journal.overall_rating,
                view_count=journal.view_count,
                recommendation_count=build_recommendation_count(journal.reactions),
                created_at=journal.created_at,
                reactions=journal.reactions,
            )
        )

    if sort == "recommendations":
        items.sort(key=lambda item: (-item.recommendation_count, -item.view_count, item.title))
    else:
        items.sort(key=lambda item: (-item.view_count, -item.recommendation_count, item.title))

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return CommunityFeedJournalListResponse(items=items[start:end], total=total, page=page, page_size=page_size)


@feed_router.get("/community-feed/journals/{journal_id}", response_model=CommunityJournalDetailResponse)
def get_community_journal_detail(
    journal_id: int,
    db: Session = Depends(get_db),
):
    row = (
        db.query(TravelJournal, Trip)
        .join(Trip, Trip.id == TravelJournal.trip_id)
        .options(
            selectinload(TravelJournal.comments).selectinload(TravelJournalComment.reactions),
            selectinload(TravelJournal.reactions),
            selectinload(TravelJournal.todos),
        )
        .filter(TravelJournal.id == journal_id, TravelJournal.share_with_community.is_(True))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community journal not found")

    journal, trip = row
    return CommunityJournalDetailResponse(
        trip_title=trip.title,
        destination=trip.destination,
        journal=journal,
    )


@feed_router.post("/community-feed/journals/{journal_id}/view", response_model=CommunityFeedJournalResponse)
def increase_community_journal_view_count(
    journal_id: int,
    db: Session = Depends(get_db),
):
    row = (
        db.query(TravelJournal, Trip)
        .join(Trip, Trip.id == TravelJournal.trip_id)
        .options(selectinload(TravelJournal.reactions))
        .filter(TravelJournal.id == journal_id, TravelJournal.share_with_community.is_(True))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community journal not found")

    journal, trip = row
    journal.view_count += 1
    db.commit()
    db.refresh(journal)
    return CommunityJournalDetailResponse(
        trip_title=trip.title,
        destination=trip.destination,
        journal=journal,
    )


@feed_router.get("/community-feed/places/top", response_model=list[CommunityPlaceCardResponse])
def get_top_community_places(
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    stats = (
        db.query(PlaceStat)
        .order_by(PlaceStat.review_count.desc(), PlaceStat.average_rating.desc(), PlaceStat.place_name.asc())
        .limit(limit)
        .all()
    )
    return [
        CommunityPlaceCardResponse(
            id=stat.id,
            city=stat.city,
            place_name=stat.place_name,
            review_count=stat.review_count,
            average_rating=stat.average_rating,
            top_tags=stat.top_tags[:2],
        )
        for stat in stats
    ]


@feed_router.get("/community-feed/places", response_model=CommunityPlaceListResponse)
def get_community_places(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=30),
    q: str | None = Query(default=None, max_length=120),
    city: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    query = db.query(PlaceStat)
    if city:
        normalized_city = city.strip().lower()
        if normalized_city:
            query = query.filter(func.lower(PlaceStat.city) == normalized_city)
    if q:
        keyword = q.strip().lower()
        if keyword:
            query = query.filter(func.lower(PlaceStat.place_name).like(f"%{keyword}%"))

    total = query.count()
    stats = (
        query.order_by(PlaceStat.review_count.desc(), PlaceStat.average_rating.desc(), PlaceStat.place_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return CommunityPlaceListResponse(
        items=[
            CommunityPlaceCardResponse(
                id=stat.id,
                city=stat.city,
                place_name=stat.place_name,
                review_count=stat.review_count,
                average_rating=stat.average_rating,
                top_tags=stat.top_tags[:2],
            )
            for stat in stats
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@feed_router.get("/community-feed/place-cities", response_model=list[CommunityPlaceCityResponse])
def get_community_place_cities(db: Session = Depends(get_db)):
    rows = (
        db.query(PlaceStat.city, func.sum(PlaceStat.review_count).label("review_count"))
        .group_by(PlaceStat.city)
        .order_by(func.sum(PlaceStat.review_count).desc(), PlaceStat.city.asc())
        .all()
    )
    return [CommunityPlaceCityResponse(city=city, review_count=int(review_count or 0)) for city, review_count in rows]


@feed_router.get("/community-feed/places/{place_stat_id}", response_model=CommunityPlaceDetailResponse)
def get_community_place_detail(
    place_stat_id: int,
    db: Session = Depends(get_db),
):
    stat = db.query(PlaceStat).filter(PlaceStat.id == place_stat_id).first()
    if stat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community place not found")

    reviews = (
        db.query(PlaceReview, Trip)
        .join(Trip, Trip.id == PlaceReview.trip_id)
        .options(selectinload(PlaceReview.reactions))
        .filter(PlaceReview.city == stat.city, PlaceReview.place_name == stat.place_name)
        .order_by(PlaceReview.created_at.desc(), PlaceReview.id.desc())
        .all()
    )
    return CommunityPlaceDetailResponse(
        place=CommunityPlaceCardResponse(
            id=stat.id,
            city=stat.city,
            place_name=stat.place_name,
            review_count=stat.review_count,
            average_rating=stat.average_rating,
            top_tags=stat.top_tags[:2],
        ),
        reviews=[
            CommunityPlaceReviewItemResponse(
                id=review.id,
                trip_id=trip.id,
                trip_title=trip.title,
                destination=trip.destination,
                city=review.city,
                place_name=review.place_name,
                rating=review.rating,
                visit_time_slot=review.visit_time_slot,
                companion_type=review.companion_type,
                recommended=review.recommended,
                would_revisit=review.would_revisit,
                tags=review.tags,
                review_text=review.review_text,
                reactions=review.reactions,
                created_at=review.created_at,
            )
            for review, trip in reviews
        ],
    )
