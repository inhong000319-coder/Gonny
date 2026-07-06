from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.domains.community_journals.services.content_blocks import (
    build_recommendation_count,
    collect_travel_journal_image_urls,
    normalize_travel_journal_content_blocks,
)
from app.models.place_review import PlaceReview, PlaceStat
from app.models.travel_journal import TravelJournal, TravelJournalComment
from app.models.trip import Trip
from app.schemas.community import (
    CommunityFeedJournalListResponse,
    CommunityFeedJournalResponse,
    CommunityFeedResponse,
    CommunityFeedReviewResponse,
    CommunityJournalDetailResponse,
    CommunityPlaceCardResponse,
    CommunityPlaceCityResponse,
    CommunityPlaceDetailResponse,
    CommunityPlaceListResponse,
    CommunityPlaceReviewItemResponse,
)


def _build_feed_journal_response(journal: TravelJournal, trip: Trip) -> CommunityFeedJournalResponse:
    normalized_blocks = normalize_travel_journal_content_blocks(
        journal.content_blocks,
        journal.diary_text,
        journal.image_urls,
    )
    image_urls = collect_travel_journal_image_urls(normalized_blocks, journal.image_urls)
    return CommunityFeedJournalResponse(
        id=journal.id,
        trip_id=trip.id,
        trip_title=trip.title,
        destination=trip.destination,
        title=journal.title,
        diary_text=journal.diary_text,
        reflection_text=journal.reflection_text,
        content_blocks=normalized_blocks,
        image_urls=image_urls,
        overall_rating=journal.overall_rating,
        view_count=journal.view_count,
        recommendation_count=build_recommendation_count(journal.reactions),
        created_at=journal.created_at,
        reactions=journal.reactions,
    )


def _build_place_card_response(stat: PlaceStat) -> CommunityPlaceCardResponse:
    return CommunityPlaceCardResponse(
        id=stat.id,
        city=stat.city,
        place_name=stat.place_name,
        review_count=stat.review_count,
        average_rating=stat.average_rating,
        top_tags=stat.top_tags[:2],
    )


class CommunityFeedService:
    def get_feed(self, *, db: Session, limit: int) -> CommunityFeedResponse:
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
            journals=[_build_feed_journal_response(journal, trip) for journal, trip in journals],
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

    def list_journals(
        self,
        *,
        db: Session,
        page: int,
        page_size: int,
        sort: str,
        q: str | None,
    ) -> CommunityFeedJournalListResponse:
        journal_rows = (
            db.query(TravelJournal, Trip)
            .join(Trip, Trip.id == TravelJournal.trip_id)
            .options(selectinload(TravelJournal.reactions))
            .filter(TravelJournal.share_with_community.is_(True))
            .all()
        )

        items: list[CommunityFeedJournalResponse] = []
        keyword = q.strip().lower() if q else None
        for journal, trip in journal_rows:
            if keyword and keyword not in journal.title.lower():
                continue
            items.append(_build_feed_journal_response(journal, trip))

        if sort == "recommendations":
            items.sort(key=lambda item: (-item.recommendation_count, -item.view_count, item.title))
        else:
            items.sort(key=lambda item: (-item.view_count, -item.recommendation_count, item.title))

        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return CommunityFeedJournalListResponse(items=items[start:end], total=total, page=page, page_size=page_size)

    def get_journal_detail(self, *, db: Session, journal_id: int) -> CommunityJournalDetailResponse:
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

    def increase_journal_view_count(self, *, db: Session, journal_id: int) -> CommunityFeedJournalResponse:
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
        return _build_feed_journal_response(journal, trip)

    def list_top_places(self, *, db: Session, limit: int) -> list[CommunityPlaceCardResponse]:
        stats = (
            db.query(PlaceStat)
            .order_by(PlaceStat.review_count.desc(), PlaceStat.average_rating.desc(), PlaceStat.place_name.asc())
            .limit(limit)
            .all()
        )
        return [_build_place_card_response(stat) for stat in stats]

    def list_places(
        self,
        *,
        db: Session,
        page: int,
        page_size: int,
        q: str | None,
        city: str | None,
    ) -> CommunityPlaceListResponse:
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
            items=[_build_place_card_response(stat) for stat in stats],
            total=total,
            page=page,
            page_size=page_size,
        )

    def list_place_cities(self, *, db: Session) -> list[CommunityPlaceCityResponse]:
        rows = (
            db.query(PlaceStat.city, func.sum(PlaceStat.review_count).label("review_count"))
            .group_by(PlaceStat.city)
            .order_by(func.sum(PlaceStat.review_count).desc(), PlaceStat.city.asc())
            .all()
        )
        return [CommunityPlaceCityResponse(city=city, review_count=int(review_count or 0)) for city, review_count in rows]

    def get_place_detail(self, *, db: Session, place_stat_id: int) -> CommunityPlaceDetailResponse:
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
            place=_build_place_card_response(stat),
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


community_feed_service = CommunityFeedService()
