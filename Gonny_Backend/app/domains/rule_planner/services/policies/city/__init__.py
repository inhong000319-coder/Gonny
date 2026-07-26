from __future__ import annotations

from types import ModuleType

from app.domains.rule_planner.schemas import NormalizedRuleRequest

from . import busan, jeju, seoul


CITY_POLICIES: dict[str, ModuleType] = {
    "busan": busan,
    "jeju": jeju,
    "seoul": seoul,
}


def _policy_for(request: NormalizedRuleRequest) -> ModuleType | None:
    return CITY_POLICIES.get(request.city)


def preferred_area_order(request: NormalizedRuleRequest, area_scores: dict[str, int]) -> list[str]:
    ranked_areas = [area for area, _ in sorted(area_scores.items(), key=lambda item: item[1], reverse=True)]
    policy = _policy_for(request)
    if policy is not None:
        return policy.preferred_area_order(request, area_scores)
    return ranked_areas


def preferred_area_match_bonus(
    request: NormalizedRuleRequest,
    preferred_area: str | None,
    place_area: str,
) -> int:
    if not preferred_area or preferred_area != place_area:
        return 0
    policy = _policy_for(request)
    if policy is not None:
        return policy.preferred_area_match_bonus()
    return 9


def same_area_continuity_bonus(
    request: NormalizedRuleRequest,
    previous_area: str | None,
    place_area: str,
) -> int:
    if not previous_area or previous_area != place_area:
        return 0
    policy = _policy_for(request)
    if policy is not None:
        return policy.same_area_continuity_bonus()
    return 10


def neighbor_area_bonus(
    request: NormalizedRuleRequest,
    previous_area: str | None,
    place_area: str,
) -> int:
    policy = _policy_for(request)
    if policy is not None:
        return policy.neighbor_area_bonus(previous_area, place_area)
    return 0


def evening_food_bonus(
    request: NormalizedRuleRequest,
    time_slot: str,
    categories: set[str],
) -> int:
    policy = _policy_for(request)
    if policy is not None:
        return policy.evening_food_bonus(time_slot, categories)
    return 0
