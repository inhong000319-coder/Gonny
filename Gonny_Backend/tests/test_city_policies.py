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


def test_busan_policy_recognizes_centum_and_dongnae_as_haeundae_neighbors() -> None:
    # centum (Udong, Haeundae-gu) and dongnae (Dongnae-gu, which borders
    # Haeundae-gu to its east) were added to the catalog for the onsen
    # places heosimchung (dongnae) and shinsegae-spaland (centum) - both
    # must actually be reachable through BUSAN_AREA_NEIGHBORS or their
    # neighbor_area_bonus silently never applies.
    busan_request = build_request("busan")

    assert neighbor_area_bonus(busan_request, "haeundae", "centum") > 0
    assert neighbor_area_bonus(busan_request, "haeundae", "dongnae") > 0
    assert neighbor_area_bonus(busan_request, "gwangalli", "centum") > 0
    # centum sits between gwangalli and haeundae, but dongnae (inland) is
    # not geographically close to the coastal downtown areas.
    assert neighbor_area_bonus(busan_request, "nampo", "dongnae") == 0
    assert neighbor_area_bonus(busan_request, "songdo", "dongnae") == 0
    assert neighbor_area_bonus(busan_request, "gwangalli", "dongnae") == 0
