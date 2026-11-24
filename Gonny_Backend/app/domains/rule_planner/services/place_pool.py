"""Pure rule functions for the place-expansion engine change (PR-A): which
places compete in the MAIN morning/afternoon/evening slot pool for a given
request, and whether a place is in season on a given day.

Deliberately has no dependency on service.py/slot_alternatives.py/
weather_alerts.py (they import this module, not the other way around) -
same "duplicated rather than circularly imported" spirit already used by
slot_alternatives.py and recalculate.py for their own service.py-mirroring
helpers.
"""
from __future__ import annotations

from datetime import date

from app.domains.destination_catalog.schemas import ALTERNATE_TIER, PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest


# Trip concept -> the theme_tags value it promotes an alternate place on -
# see is_main_pool_member. Only concepts with a real theme-tag equivalent
# belong here; a concept with no entry simply never promotes anything.
THEME_TAG_BY_CONCEPT: dict[str, str] = {
    "walk": "walk",
    "sports": "sports",
}


def is_in_season(place: PlaceData, day_date: date | None) -> bool:
    """True when place has no season_months restriction, or day_date is
    unknown (no start_date on the request - same "no filter without a
    date" rule as closed-day exclusion), or day_date's month is one of
    place.season_months."""
    if not place.season_months or day_date is None:
        return True
    return day_date.month in place.season_months


def theme_tags_for_request(request: NormalizedRuleRequest) -> set[str]:
    """The theme_tags an alternate place can match to get promoted into
    the main pool for this request - derived from request.concepts via
    THEME_TAG_BY_CONCEPT, never from place data."""
    return {THEME_TAG_BY_CONCEPT[concept] for concept in request.concepts if concept in THEME_TAG_BY_CONCEPT}


def is_main_pool_member(place: PlaceData, request: NormalizedRuleRequest) -> bool:
    """Whether place belongs in _build_items' main scored_places pool.

    True for every non-alternate place (mvp_tier != ALTERNATE_TIER) - the
    existing behavior, unchanged. An alternate place is only True when its
    theme_tags overlap theme_tags_for_request(request) (theme promotion) -
    otherwise it stays alternate-only (available via slot_alternatives.py
    and weather_alerts.py's indoor swap candidates, never in items).
    """
    if place.mvp_tier != ALTERNATE_TIER:
        return True
    return bool(set(place.theme_tags) & theme_tags_for_request(request))
