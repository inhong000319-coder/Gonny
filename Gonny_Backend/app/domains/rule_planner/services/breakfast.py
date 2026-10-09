"""Breakfast-candidate classification for the independent breakfast
recommendation (see RuleItineraryRequest.include_breakfast).

The place catalog has almost no verified opening-hours data for food
places (14 of 227 "food"-tagged places across seoul/busan/jeju have any
open_hours text at all, and only 5 of those are a parseable time range),
so "is this place open at breakfast time" can't be judged from hours data.
Instead this classifies by keyword signal only - a place is a breakfast
candidate if its name/summary/highlight_tags/mood_keywords say it's a
market, cafe, bakery, or brunch spot, or mention morning/breakfast
explicitly. See the PR description for the per-city candidate list this
produced - it's meant to be eyeballed, not trusted blindly.
"""

from __future__ import annotations

from app.domains.destination_catalog.schemas import PlaceData

# Matched against place.name only. Many restaurant summaries mention a
# market only as a nearby landmark ("OO시장 인근" - "near OO market"),
# which is a location reference, not a signal that the place itself is a
# market - so this is deliberately name-only, not summary-wide.
BREAKFAST_MARKET_KEYWORDS = ["시장", "market"]

# Matched against name + summary + highlight_tags + mood_keywords - these
# words are specific enough (unlike "시장") that a summary mentioning them
# is almost always describing the place itself, e.g. "브런치 전문점"
# ("brunch specialist") in a restaurant's own one-line summary.
BREAKFAST_KEYWORDS = [
    "카페",
    "cafe",
    "coffee",
    "베이커리",
    "bakery",
    "브런치",
    "brunch",
    "아침",
    "모닝",
    "조식",
    "morning",
    "breakfast",
]


def is_breakfast_candidate(place: PlaceData) -> bool:
    name = place.name.lower()
    if any(keyword in name for keyword in BREAKFAST_MARKET_KEYWORDS):
        return True

    haystack = " ".join(
        [place.name, place.summary, *place.highlight_tags, *place.mood_keywords]
    ).lower()
    return any(keyword in haystack for keyword in BREAKFAST_KEYWORDS)
