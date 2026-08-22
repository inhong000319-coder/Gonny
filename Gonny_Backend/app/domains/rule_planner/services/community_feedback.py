from __future__ import annotations

from dataclasses import dataclass, field

MIN_TOTAL_REVIEWS = 5
MIN_DETAIL_REVIEWS = 3

VALID_TIME_SLOTS = {"morning", "afternoon", "evening"}
VALID_COMPANION_TYPES = {"solo", "couple", "friend", "family"}


@dataclass(frozen=True)
class PlaceFeedbackSignal:
    """A DB-independent snapshot of one place's PlaceStat.

    The caller (load_place_feedback_signals) resolves this ahead of time
    from the database, so community_feedback_bonus() below never touches
    the database itself - same separation as coordinate_area_transition_bonus
    receiving PlaceData objects that already have their coordinates filled in.
    """

    review_count: int
    average_rating: float
    slot_scores: dict[str, float] = field(default_factory=dict)
    slot_review_counts: dict[str, int] = field(default_factory=dict)
    companion_scores: dict[str, float] = field(default_factory=dict)
    companion_review_counts: dict[str, int] = field(default_factory=dict)


def _rating_to_score(rating: float) -> int:
    """Linear scale matching other slot_score bonus magnitudes (+8, +12,
    etc.): rating 5 -> +10, rating 3 -> 0, rating 1 -> -10."""
    return round((rating - 3) * 5)


def community_feedback_bonus(
    signal: PlaceFeedbackSignal | None,
    time_slot: str,
    companion_type: str,
) -> int | None:
    """Review-based bonus for a slot, or None if there isn't enough
    trustworthy review data - callers should apply no adjustment in that
    case, the same None-on-missing-data contract as
    coordinate_area_transition_bonus.

    Only engages once the place has >= MIN_TOTAL_REVIEWS reviews overall
    (this is also the gate PlaceFeedbackSignal.review_count encodes - see
    load_place_feedback_signals, which only includes places whose
    PlaceStat.place_id exactly matches our catalog's place_id). Within
    that, slot_scores[time_slot]/companion_scores[companion_type] are only
    used when at least MIN_DETAIL_REVIEWS reviews back that specific
    bucket, and only for our system's recognized time_slot/companion_type
    values - free-text values entered elsewhere (typos, Korean, etc.) are
    silently ignored rather than guessed at.
    """
    if signal is None or signal.review_count < MIN_TOTAL_REVIEWS:
        return None

    ratings: list[float] = []

    if time_slot in VALID_TIME_SLOTS and signal.slot_review_counts.get(time_slot, 0) >= MIN_DETAIL_REVIEWS:
        ratings.append(signal.slot_scores[time_slot])

    if (
        companion_type in VALID_COMPANION_TYPES
        and signal.companion_review_counts.get(companion_type, 0) >= MIN_DETAIL_REVIEWS
    ):
        ratings.append(signal.companion_scores[companion_type])

    if not ratings:
        # No slot/companion-specific bucket is trustworthy enough on its
        # own; fall back to the place's overall average, which is already
        # gated by review_count >= MIN_TOTAL_REVIEWS above.
        ratings.append(signal.average_rating)

    return _rating_to_score(sum(ratings) / len(ratings))


def load_place_feedback_signals(place_ids: list[str]) -> dict[str, PlaceFeedbackSignal]:
    """Batch-loads PlaceFeedbackSignal for the given place_ids in one query.

    Best-effort and self-contained: opens and closes its own short-lived
    session, and returns {} on any failure (no DATABASE_URL configured,
    the place_stats table not migrated yet, a connection error, etc.)
    rather than raising - the rule_planner scoring pipeline has never
    depended on the database, and reviews being unreachable should degrade
    to "no bonus", not break itinerary generation. With no reviews at all
    (the current state), this always returns {}, so community_feedback_bonus()
    is a no-op everywhere.

    Matches strictly on PlaceStat.place_id against our catalog's place_id
    (no name-based fuzzy matching, no city filter - place_id is already
    globally unique across our catalog, and PlaceReview.city is free-text
    entered by users so it isn't a reliable join key). A PlaceStat row with
    place_id unset or pointing at a different id is simply not returned here.
    """
    if not place_ids:
        return {}

    try:
        from app.db.session import SessionLocal
        from app.models.place_review import PlaceStat

        if SessionLocal is None:
            return {}

        db = SessionLocal()
        try:
            stats = db.query(PlaceStat).filter(PlaceStat.place_id.in_(place_ids)).all()
        finally:
            db.close()
    except Exception:
        return {}

    signals: dict[str, PlaceFeedbackSignal] = {}
    for stat in stats:
        if not stat.place_id:
            continue
        signals[stat.place_id] = PlaceFeedbackSignal(
            review_count=stat.review_count,
            average_rating=stat.average_rating,
            slot_scores=dict(stat.slot_scores or {}),
            slot_review_counts=dict(stat.slot_review_counts or {}),
            companion_scores=dict(stat.companion_scores or {}),
            companion_review_counts=dict(stat.companion_review_counts or {}),
        )
    return signals
