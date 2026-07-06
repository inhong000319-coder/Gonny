from __future__ import annotations

from fastapi import HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domains.trips.services.service import trip_service
from app.models.place_review import PlaceReview, PlaceReviewReaction
from app.models.travel_journal import TravelJournal
from app.schemas.community import (
    PlaceReviewCreate,
    PlaceReviewReactionCreate,
    PlaceReviewUpdate,
    PlaceSuggestionResponse,
    TagSuggestionResponse,
)
from app.services.place_review_stats_service import refresh_place_stat


def _sanitize_tags(tags: list[str]) -> list[str]:
    return [tag.strip() for tag in tags if tag.strip()]


class CommunityReviewService:
    def create_review(self, *, db: Session, trip_id: int, payload: PlaceReviewCreate) -> PlaceReview:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)
        if payload.journal_id is not None:
            journal = (
                db.query(TravelJournal)
                .filter(TravelJournal.id == payload.journal_id, TravelJournal.trip_id == trip_id)
                .first()
            )
            if journal is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel journal not found")

        review = PlaceReview(
            trip_id=trip_id,
            journal_id=payload.journal_id,
            city=payload.city.strip().lower(),
            place_id=payload.place_id,
            place_name=payload.place_name.strip(),
            rating=payload.rating,
            visit_time_slot=payload.visit_time_slot,
            companion_type=payload.companion_type,
            recommended=payload.recommended,
            would_revisit=payload.would_revisit,
            tags=_sanitize_tags(payload.tags),
            review_text=payload.review_text,
        )
        db.add(review)
        db.flush()
        refresh_place_stat(db=db, city=review.city, place_name=review.place_name)
        db.commit()
        db.refresh(review)
        return review

    def update_review(
        self,
        *,
        db: Session,
        trip_id: int,
        review_id: int,
        payload: PlaceReviewUpdate,
    ) -> PlaceReview:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)
        review = (
            db.query(PlaceReview)
            .filter(PlaceReview.id == review_id, PlaceReview.trip_id == trip_id)
            .first()
        )
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
            review.tags = _sanitize_tags(payload.tags)
        if payload.review_text is not None:
            review.review_text = payload.review_text

        db.flush()
        refresh_place_stat(db=db, city=review.city, place_name=review.place_name)
        if original_city != review.city or original_place_name != review.place_name:
            refresh_place_stat(db=db, city=original_city, place_name=original_place_name)
        db.commit()
        db.refresh(review)
        return review

    def delete_review(self, *, db: Session, trip_id: int, review_id: int) -> None:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)
        review = (
            db.query(PlaceReview)
            .filter(PlaceReview.id == review_id, PlaceReview.trip_id == trip_id)
            .first()
        )
        if review is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place review not found")

        original_city = review.city
        original_place_name = review.place_name
        db.delete(review)
        db.flush()
        refresh_place_stat(db=db, city=original_city, place_name=original_place_name)
        db.commit()

    def create_review_reaction(
        self,
        *,
        db: Session,
        trip_id: int,
        review_id: int,
        payload: PlaceReviewReactionCreate,
        response: Response,
    ) -> PlaceReviewReaction | None:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)
        review = (
            db.query(PlaceReview)
            .filter(PlaceReview.id == review_id, PlaceReview.trip_id == trip_id)
            .first()
        )
        if review is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place review not found")

        reaction_type = payload.reaction_type.strip()
        delta = 1 if payload.delta >= 0 else -1
        reaction = (
            db.query(PlaceReviewReaction)
            .filter(
                PlaceReviewReaction.review_id == review_id,
                PlaceReviewReaction.reaction_type == reaction_type,
            )
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

    def list_place_suggestions(
        self,
        *,
        db: Session,
        trip_id: int,
        q: str,
        limit: int,
    ) -> list[PlaceSuggestionResponse]:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)

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
            .order_by(
                func.count(PlaceReview.id).desc(),
                func.avg(PlaceReview.rating).desc(),
                PlaceReview.place_name.asc(),
            )
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

    def list_tag_suggestions(
        self,
        *,
        db: Session,
        trip_id: int,
        q: str,
        limit: int,
    ) -> list[TagSuggestionResponse]:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)

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


community_review_service = CommunityReviewService()
