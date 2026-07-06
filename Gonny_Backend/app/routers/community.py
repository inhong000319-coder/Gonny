from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.domains.community_feed.services import community_feed_service
from app.domains.community_journals.services import community_journal_service
from app.domains.community_reviews.services import community_review_service
from app.domains.trips.services.service import trip_service
from app.models.place_review import PlaceReview, PlaceStat
from app.models.travel_journal import (
    TravelJournal,
    TravelJournalComment,
    TripTodo,
)
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


router = APIRouter(prefix="/trips/{trip_id}", tags=["trip-community"])
feed_router = APIRouter(tags=["community-feed"])


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


@router.get("/community", response_model=TripCommunityResponse)
def get_trip_community(trip_id: int, db: Session = Depends(get_db)):
    trip_service.get_trip_or_404(db=db, trip_id=trip_id)

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
    return community_journal_service.upload_image(db=db, trip_id=trip_id, image=image)


@router.post("/community/todos", response_model=TripTodoResponse, status_code=status.HTTP_201_CREATED)
def create_trip_todo(
    trip_id: int,
    todo: TripTodoCreate,
    db: Session = Depends(get_db),
):
    trip_service.get_trip_or_404(db=db, trip_id=trip_id)
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
    trip_service.get_trip_or_404(db=db, trip_id=trip_id)
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
    return community_journal_service.create_journal(db=db, trip_id=trip_id, payload=journal)


@router.patch("/community/journals/{journal_id}", response_model=TravelJournalResponse)
def update_travel_journal(
    trip_id: int,
    journal_id: int,
    payload: TravelJournalUpdate,
    db: Session = Depends(get_db),
):
    return community_journal_service.update_journal(
        db=db,
        trip_id=trip_id,
        journal_id=journal_id,
        payload=payload,
    )


@router.delete("/community/journals/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_travel_journal(
    trip_id: int,
    journal_id: int,
    db: Session = Depends(get_db),
):
    community_journal_service.delete_journal(db=db, trip_id=trip_id, journal_id=journal_id)


@router.post("/community/journals/{journal_id}/comments", response_model=TravelJournalCommentResponse, status_code=status.HTTP_201_CREATED)
def create_travel_journal_comment(
    trip_id: int,
    journal_id: int,
    payload: TravelJournalCommentCreate,
    actor: dict[str, str | None] = Depends(resolve_actor),
    db: Session = Depends(get_db),
):
    return community_journal_service.create_comment(
        db=db,
        trip_id=trip_id,
        journal_id=journal_id,
        payload=payload,
        actor=actor,
    )


@router.patch("/community/journals/{journal_id}/comments/{comment_id}", response_model=TravelJournalCommentResponse)
def update_travel_journal_comment(
    trip_id: int,
    journal_id: int,
    comment_id: int,
    payload: TravelJournalCommentUpdate,
    actor: dict[str, str | None] = Depends(resolve_actor),
    db: Session = Depends(get_db),
):
    return community_journal_service.update_comment(
        db=db,
        trip_id=trip_id,
        journal_id=journal_id,
        comment_id=comment_id,
        payload=payload,
        actor=actor,
    )


@router.delete("/community/journals/{journal_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_travel_journal_comment(
    trip_id: int,
    journal_id: int,
    comment_id: int,
    actor: dict[str, str | None] = Depends(resolve_actor),
    db: Session = Depends(get_db),
):
    community_journal_service.delete_comment(
        db=db,
        trip_id=trip_id,
        journal_id=journal_id,
        comment_id=comment_id,
        actor=actor,
    )


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
    return community_journal_service.create_comment_reaction(
        db=db,
        trip_id=trip_id,
        journal_id=journal_id,
        comment_id=comment_id,
        payload=payload,
        response=response,
    )


@router.post(
    "/community/journals/{journal_id}/reactions",
    response_model=TravelJournalReactionResponse | None,
    status_code=status.HTTP_201_CREATED,
)
def create_travel_journal_reaction(
    trip_id: int,
    journal_id: int,
    payload: TravelJournalReactionCreate,
    response: Response,
    db: Session = Depends(get_db),
):
    return community_journal_service.create_journal_reaction(
        db=db,
        trip_id=trip_id,
        journal_id=journal_id,
        payload=payload,
        response=response,
    )


@router.post("/community/reviews", response_model=PlaceReviewResponse, status_code=status.HTTP_201_CREATED)
def create_place_review(
    trip_id: int,
    review: PlaceReviewCreate,
    db: Session = Depends(get_db),
):
    return community_review_service.create_review(db=db, trip_id=trip_id, payload=review)


@router.patch("/community/reviews/{review_id}", response_model=PlaceReviewResponse)
def update_place_review(
    trip_id: int,
    review_id: int,
    payload: PlaceReviewUpdate,
    db: Session = Depends(get_db),
):
    return community_review_service.update_review(
        db=db,
        trip_id=trip_id,
        review_id=review_id,
        payload=payload,
    )


@router.delete("/community/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_place_review(
    trip_id: int,
    review_id: int,
    db: Session = Depends(get_db),
):
    community_review_service.delete_review(db=db, trip_id=trip_id, review_id=review_id)


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
    return community_review_service.create_review_reaction(
        db=db,
        trip_id=trip_id,
        review_id=review_id,
        payload=payload,
        response=response,
    )


@router.get("/community/place-suggestions", response_model=list[PlaceSuggestionResponse])
def get_place_suggestions(
    trip_id: int,
    q: str = Query(min_length=1, max_length=60),
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return community_review_service.list_place_suggestions(
        db=db,
        trip_id=trip_id,
        q=q,
        limit=limit,
    )


@router.get("/community/tag-suggestions", response_model=list[TagSuggestionResponse])
def get_tag_suggestions(
    trip_id: int,
    q: str = Query(min_length=1, max_length=40),
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return community_review_service.list_tag_suggestions(
        db=db,
        trip_id=trip_id,
        q=q,
        limit=limit,
    )


@feed_router.get("/community-feed", response_model=CommunityFeedResponse)
def get_community_feed(
    limit: int = Query(default=24, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return community_feed_service.get_feed(db=db, limit=limit)


@feed_router.get("/community-feed/journals", response_model=CommunityFeedJournalListResponse)
def get_community_feed_journals(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=30),
    sort: str = Query(default="views"),
    q: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    return community_feed_service.list_journals(
        db=db,
        page=page,
        page_size=page_size,
        sort=sort,
        q=q,
    )


@feed_router.get("/community-feed/journals/{journal_id}", response_model=CommunityJournalDetailResponse)
def get_community_journal_detail(
    journal_id: int,
    db: Session = Depends(get_db),
):
    return community_feed_service.get_journal_detail(db=db, journal_id=journal_id)


@feed_router.post("/community-feed/journals/{journal_id}/view", response_model=CommunityFeedJournalResponse)
def increase_community_journal_view_count(
    journal_id: int,
    db: Session = Depends(get_db),
):
    return community_feed_service.increase_journal_view_count(db=db, journal_id=journal_id)


@feed_router.get("/community-feed/places/top", response_model=list[CommunityPlaceCardResponse])
def get_top_community_places(
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return community_feed_service.list_top_places(db=db, limit=limit)


@feed_router.get("/community-feed/places", response_model=CommunityPlaceListResponse)
def get_community_places(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=30),
    q: str | None = Query(default=None, max_length=120),
    city: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    return community_feed_service.list_places(
        db=db,
        page=page,
        page_size=page_size,
        q=q,
        city=city,
    )


@feed_router.get("/community-feed/place-cities", response_model=list[CommunityPlaceCityResponse])
def get_community_place_cities(db: Session = Depends(get_db)):
    return community_feed_service.list_place_cities(db=db)


@feed_router.get("/community-feed/places/{place_stat_id}", response_model=CommunityPlaceDetailResponse)
def get_community_place_detail(
    place_stat_id: int,
    db: Session = Depends(get_db),
):
    return community_feed_service.get_place_detail(db=db, place_stat_id=place_stat_id)
