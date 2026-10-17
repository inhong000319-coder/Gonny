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


# Measured (local_only/reports/headroom_and_variants_analysis.md): replacing
# the single reference_point tiered bonus with this per-day-endpoint average
# distance penalty, unrounded, at -4.0/km, took seoul's average
# accommodation-to-itinerary distance from 5.21km to 4.56km, collapsed the
# top1/top2 score-tie rate from 49.0% to 2.1% (the old tiered bonus awards
# only 4 discrete integer values, so unrelated candidates constantly landed
# on the same score - see accommodation_scoring.py's CLOSE/NEARBY/FAR
# tiers), and brought budget/companion fit to 100% (from 99%/99%). Left
# unrounded deliberately - round() is what caused the tie collapse at
# every coefficient tested, including this one.
ACCOMMODATION_DISTANCE_PENALTY_PER_KM = -4.0


def accommodation_distance_score(distances_km: list[float]) -> float:
    if not distances_km:
        return 0.0
    average_km = sum(distances_km) / len(distances_km)
    return average_km * ACCOMMODATION_DISTANCE_PENALTY_PER_KM
