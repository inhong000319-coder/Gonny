from __future__ import annotations

from collections import defaultdict

from app.domains.rule_planner.schemas import NormalizedRuleRequest

from ...constants import SEOUL_AREA_NEIGHBORS, SEOUL_AREA_ROUTE_ORDER


def preferred_area_order(request: NormalizedRuleRequest, area_scores: dict[str, int]) -> list[str]:
    concept_weights: dict[str, int] = defaultdict(int)
    if "culture" in request.concepts:
        for area in ("jongno", "euljiro", "dongdaemun"):
            concept_weights[area] += 18
    if "food" in request.concepts:
        for area in ("euljiro", "hongdae", "seongsu", "itaewon", "jongno"):
            concept_weights[area] += 16
    if "relax" in request.concepts:
        for area in ("yeouido", "jamsil", "seongsu", "jongno"):
            concept_weights[area] += 12
    if "shopping" in request.concepts:
        for area in ("seongsu", "gangnam", "myeongdong", "hongdae"):
            concept_weights[area] += 10
    if request.companion_type == "friend":
        for area in ("euljiro", "hongdae", "seongsu", "itaewon"):
            concept_weights[area] += 8

    return sorted(
        area_scores.keys(),
        key=lambda area: (
            area_scores[area] + concept_weights[area] + (6 if area in SEOUL_AREA_ROUTE_ORDER else 0),
            -SEOUL_AREA_ROUTE_ORDER.index(area) if area in SEOUL_AREA_ROUTE_ORDER else 0,
        ),
        reverse=True,
    )


def preferred_area_match_bonus() -> int:
    return 14


def same_area_continuity_bonus() -> int:
    return 18


def neighbor_area_bonus(previous_area: str | None, place_area: str) -> int:
    if not previous_area:
        return 0
    if place_area in SEOUL_AREA_NEIGHBORS.get(previous_area, set()):
        return 8
    return 0


def evening_food_bonus(time_slot: str, categories: set[str]) -> int:
    if time_slot == "evening" and {"food", "nightlife"} & categories:
        return 6
    return 0
