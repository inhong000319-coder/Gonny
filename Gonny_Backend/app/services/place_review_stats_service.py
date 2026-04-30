from __future__ import annotations

from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from app.models.place_review import PlaceReview, PlaceStat


def refresh_place_stat(*, db: Session, city: str, place_name: str) -> PlaceStat:
    reviews = (
        db.query(PlaceReview)
        .filter(PlaceReview.city == city, PlaceReview.place_name == place_name)
        .order_by(PlaceReview.id.asc())
        .all()
    )

    stat = db.query(PlaceStat).filter(PlaceStat.city == city, PlaceStat.place_name == place_name).first()
    if stat is None:
        stat = PlaceStat(city=city, place_name=place_name)
        db.add(stat)

    if not reviews:
        stat.place_id = None
        stat.review_count = 0
        stat.average_rating = 0.0
        stat.recommendation_rate = 0.0
        stat.revisit_rate = 0.0
        stat.top_tags = []
        stat.slot_scores = {}
        stat.companion_scores = {}
        db.flush()
        return stat

    stat.place_id = next((review.place_id for review in reviews if review.place_id), None)
    stat.review_count = len(reviews)
    stat.average_rating = round(sum(review.rating for review in reviews) / len(reviews), 2)
    stat.recommendation_rate = round(sum(1 for review in reviews if review.recommended) / len(reviews), 2)
    stat.revisit_rate = round(sum(1 for review in reviews if review.would_revisit) / len(reviews), 2)

    tag_counter: Counter[str] = Counter()
    slot_ratings: defaultdict[str, list[int]] = defaultdict(list)
    companion_ratings: defaultdict[str, list[int]] = defaultdict(list)

    for review in reviews:
        for tag in review.tags or []:
            normalized_tag = tag.strip()
            if normalized_tag:
                tag_counter[normalized_tag] += 1
        if review.visit_time_slot:
            slot_ratings[review.visit_time_slot].append(review.rating)
        if review.companion_type:
            companion_ratings[review.companion_type].append(review.rating)

    stat.top_tags = [tag for tag, _ in tag_counter.most_common(5)]
    stat.slot_scores = {slot: round(sum(values) / len(values), 2) for slot, values in slot_ratings.items() if values}
    stat.companion_scores = {
        companion: round(sum(values) / len(values), 2) for companion, values in companion_ratings.items() if values
    }
    db.flush()
    return stat
