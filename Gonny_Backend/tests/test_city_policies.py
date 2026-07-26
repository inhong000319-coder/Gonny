from app.domains.rule_planner.schemas import NormalizedRuleRequest
from app.domains.rule_planner.services.policies.city import neighbor_area_bonus, preferred_area_order


def build_request(city: str, concepts: list[str] | None = None) -> NormalizedRuleRequest:
    return NormalizedRuleRequest(
        continent="asia",
        country="korea",
        city=city,
        travelers=2,
        nights=2,
        days=3,
        budget_band="medium",
        concepts=concepts or ["sightseeing"],
        style="easy",
        companion_type="friend",
    )


def test_busan_policy_prefers_nampo_for_food_trip() -> None:
    request = build_request("busan", concepts=["food"])

    order = preferred_area_order(
        request,
        {"haeundae": 100, "gwangalli": 100, "nampo": 100, "songdo": 100},
    )

    assert order[0] == "nampo"


def test_jeju_policy_prefers_seongsan_for_activity_trip() -> None:
    request = build_request("jeju", concepts=["activity"])

    order = preferred_area_order(
        request,
        {
            "east-jeju": 100,
            "west-jeju": 100,
            "seogwipo-west": 100,
            "seongsan": 100,
        },
    )

    assert order[0] == "seongsan"


def test_city_policy_neighbor_bonus_only_rewards_linked_areas() -> None:
    busan_request = build_request("busan")
    jeju_request = build_request("jeju")

    assert neighbor_area_bonus(busan_request, "nampo", "songdo") > 0
    assert neighbor_area_bonus(busan_request, "nampo", "haeundae") == 0
    assert neighbor_area_bonus(jeju_request, "east-jeju", "seongsan") > 0
    assert neighbor_area_bonus(jeju_request, "east-jeju", "west-jeju") == 0
