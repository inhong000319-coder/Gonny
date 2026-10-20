from __future__ import annotations

from collections import defaultdict

from app.domains.rule_planner.schemas import NormalizedRuleRequest

from ...constants import BUSAN_AREA_NEIGHBORS, BUSAN_AREA_ROUTE_ORDER

# Deliberately does NOT define price_exact_match_bonus() - busan keeps the
# shared default (10, policies/city/__init__.py.price_exact_match_bonus's
# fallback). Measured (local_only/reports/accommodation_price_bonus_
# sensitivity.md): busan's dominant pick (라발스호텔) wins on the distance
# term, not price data, so lowering this bonus only removed OTHER
# candidates' one competitive edge and made the existing concentration
# worse (top1 share 49.0%->69.8%, Grid2) - the opposite of seoul/jeju.


def preferred_area_order(request: NormalizedRuleRequest, area_scores: dict[str, int]) -> list[str]:
    concept_weights: dict[str, int] = defaultdict(int)
    if "food" in request.concepts:
        for area in ("nampo", "gwangalli", "songdo"):
            concept_weights[area] += 16
    if "shopping" in request.concepts:
        for area in ("nampo", "haeundae"):
            concept_weights[area] += 12
    if "culture" in request.concepts:
        for area in ("nampo", "songdo"):
            concept_weights[area] += 14
    if "relax" in request.concepts:
        for area in ("haeundae", "gwangalli", "songdo"):
            concept_weights[area] += 12
    if "activity" in request.concepts:
        for area in ("haeundae", "songdo"):
            concept_weights[area] += 18
    if request.companion_type == "friend":
        for area in ("gwangalli", "nampo", "haeundae"):
            concept_weights[area] += 8
    if request.companion_type == "family":
        for area in ("haeundae", "songdo"):
            concept_weights[area] += 8

    return sorted(
        area_scores.keys(),
        key=lambda area: (
            area_scores[area] + concept_weights[area] + (6 if area in BUSAN_AREA_ROUTE_ORDER else 0),
            -BUSAN_AREA_ROUTE_ORDER.index(area) if area in BUSAN_AREA_ROUTE_ORDER else 0,
        ),
        reverse=True,
    )


def preferred_area_match_bonus() -> int:
    return 11


def same_area_continuity_bonus() -> int:
    return 12


def neighbor_area_bonus(previous_area: str | None, place_area: str) -> int:
    if not previous_area:
        return 0
    if place_area in BUSAN_AREA_NEIGHBORS.get(previous_area, set()):
        return 6
    return 0


def evening_food_bonus(time_slot: str, categories: set[str]) -> int:
    if time_slot == "evening" and {"food", "nightlife"} & categories:
        return 5
    return 0


# Measured (local_only/reports/headroom_and_variants_analysis.md): busan's
# candidates already had a large reference_point score gap (median 8.0), so
# an additive distance term at -0.6~-2.0/km never changed a single pick in
# the 96-request sweep. Only the replacing form moves anything, and -4.0 was
# the coefficient where average distance (5.42km -> 5.44km) stayed
# essentially flat while budget fit improved (66.7% -> 83.3%). Left
# unrounded for the same reason as seoul (round() caused tie collapse there;
# busan had 0% ties either way, but there's no reason to round one city and
# not the other for the same hook).
ACCOMMODATION_DISTANCE_PENALTY_PER_KM = -4.0


def accommodation_distance_score(distances_km: list[float]) -> float:
    if not distances_km:
        return 0.0
    average_km = sum(distances_km) / len(distances_km)
    return average_km * ACCOMMODATION_DISTANCE_PENALTY_PER_KM
