from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from app.domains.community_journals.services.content_blocks import (
    build_travel_journal_summary,
    collect_travel_journal_image_urls,
    normalize_travel_journal_content_blocks,
)
from app.domains.trips.services.service import trip_service
from app.models.travel_journal import (
    TravelJournal,
    TravelJournalComment,
    TravelJournalCommentReaction,
    TravelJournalReaction,
)
from app.schemas.community import (
    JournalImageUploadResponse,
    TravelJournalCommentCreate,
    TravelJournalCommentReactionCreate,
    TravelJournalCommentUpdate,
    TravelJournalCreate,
    TravelJournalReactionCreate,
    TravelJournalUpdate,
)


UPLOADS_DIR = Path(__file__).resolve().parents[3] / "uploads"


def _can_edit_comment(actor: dict[str, str | None], comment: TravelJournalComment) -> bool:
    if not actor.get("user_id") or not comment.author_id:
        return True
    return actor["user_id"] == comment.author_id


def _can_delete_comment(actor: dict[str, str | None], comment: TravelJournalComment) -> bool:
    if not actor.get("user_id") or not comment.author_id:
        return True
    return actor["user_id"] == comment.author_id or actor.get("user_role") == "admin"


class CommunityJournalService:
    def upload_image(self, *, db: Session, trip_id: int, image: UploadFile) -> JournalImageUploadResponse:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)
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

    def create_journal(self, *, db: Session, trip_id: int, payload: TravelJournalCreate) -> TravelJournal:
        trip = trip_service.get_trip_or_404(db=db, trip_id=trip_id)
        normalized_blocks = normalize_travel_journal_content_blocks(
            payload.content_blocks,
            payload.diary_text,
            payload.image_urls,
        )
        image_urls = collect_travel_journal_image_urls(normalized_blocks, payload.image_urls)
        if len(image_urls) > 20:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can upload up to 20 images")

        journal = TravelJournal(
            trip_id=trip_id,
            title=payload.title,
            diary_text=build_travel_journal_summary(normalized_blocks, payload.diary_text),
            reflection_text=payload.reflection_text,
            content_blocks=normalized_blocks,
            image_urls=image_urls,
            overall_rating=payload.overall_rating,
            share_with_community=payload.share_with_community,
        )
        trip.travel_journals.append(journal)
        db.commit()
        db.refresh(journal)
        return journal

    def update_journal(
        self,
        *,
        db: Session,
        trip_id: int,
        journal_id: int,
        payload: TravelJournalUpdate,
    ) -> TravelJournal:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)
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

    def delete_journal(self, *, db: Session, trip_id: int, journal_id: int) -> None:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)
        journal = db.query(TravelJournal).filter(TravelJournal.id == journal_id, TravelJournal.trip_id == trip_id).first()
        if journal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel journal not found")

        db.delete(journal)
        db.commit()

    def create_comment(
        self,
        *,
        db: Session,
        trip_id: int,
        journal_id: int,
        payload: TravelJournalCommentCreate,
        actor: dict[str, str | None],
    ) -> TravelJournalComment:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)
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

    def update_comment(
        self,
        *,
        db: Session,
        trip_id: int,
        journal_id: int,
        comment_id: int,
        payload: TravelJournalCommentUpdate,
        actor: dict[str, str | None],
    ) -> TravelJournalComment:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)
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
        if not _can_edit_comment(actor, comment):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the author can edit this comment")

        comment.content = payload.content.strip()
        db.commit()
        db.refresh(comment)
        return comment

    def delete_comment(
        self,
        *,
        db: Session,
        trip_id: int,
        journal_id: int,
        comment_id: int,
        actor: dict[str, str | None],
    ) -> None:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)
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
        if not _can_delete_comment(actor, comment):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the author or an admin can delete this comment",
            )

        db.delete(comment)
        db.commit()

    def create_comment_reaction(
        self,
        *,
        db: Session,
        trip_id: int,
        journal_id: int,
        comment_id: int,
        payload: TravelJournalCommentReactionCreate,
        response: Response,
    ) -> TravelJournalCommentReaction | None:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)
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

    def create_journal_reaction(
        self,
        *,
        db: Session,
        trip_id: int,
        journal_id: int,
        payload: TravelJournalReactionCreate,
        response: Response,
    ) -> TravelJournalReaction | None:
        trip_service.get_trip_or_404(db=db, trip_id=trip_id)
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


community_journal_service = CommunityJournalService()
