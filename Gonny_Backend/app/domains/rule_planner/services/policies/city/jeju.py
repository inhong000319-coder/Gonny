from __future__ import annotations

from collections import defaultdict

from app.domains.rule_planner.schemas import NormalizedRuleRequest

from ...constants import JEJU_AREA_NEIGHBORS, JEJU_AREA_ROUTE_ORDER


def preferred_area_order(request: NormalizedRuleRequest, area_scores: dict[str, int]) -> list[str]:
    concept_weights: dict[str, int] = defaultdict(int)
    if "activity" in request.concepts:
        concept_weights["seongsan"] += 24
        concept_weights["east-jeju"] += 14
    if "nature" in request.concepts:
        for area in ("east-jeju", "seogwipo-west", "west-jeju", "seongsan"):
            concept_weights[area] += 14
    if "relax" in request.concepts:
        for area in ("west-jeju", "east-jeju", "seogwipo-west"):
            concept_weights[area] += 12
    if "food" in request.concepts:
        for area in ("east-jeju", "west-jeju"):
            concept_weights[area] += 10
    if "culture" in request.concepts:
        for area in ("east-jeju", "seogwipo-west"):
            concept_weights[area] += 9
    if request.companion_type == "friend":
        for area in ("east-jeju", "west-jeju", "seogwipo-west"):
            concept_weights[area] += 6
    if request.companion_type == "family":
        for area in ("seongsan", "west-jeju", "east-jeju"):
            concept_weights[area] += 8

    return sorted(
        area_scores.keys(),
        key=lambda area: (
            area_scores[area] + concept_weights[area] + (6 if area in JEJU_AREA_ROUTE_ORDER else 0),
            -JEJU_AREA_ROUTE_ORDER.index(area) if area in JEJU_AREA_ROUTE_ORDER else 0,
        ),
        reverse=True,
    )


def preferred_area_match_bonus() -> int:
    return 10


def same_area_continuity_bonus() -> int:
    return 12


def neighbor_area_bonus(previous_area: str | None, place_area: str) -> int:
    if not previous_area:
        return 0
    if place_area in JEJU_AREA_NEIGHBORS.get(previous_area, set()):
        return 5
    return 0


def evening_food_bonus(time_slot: str, categories: set[str]) -> int:
    if time_slot == "evening" and "food" in categories:
        return 3
    return 0
