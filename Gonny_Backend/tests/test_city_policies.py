from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest
from app.domains.rule_planner.services.policies.city import neighbor_area_bonus, pick_day_area, preferred_area_order
from app.domains.rule_planner.services.policies.city.jeju import pick_day_area as jeju_pick_day_area


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


def build_place(**overrides) -> PlaceData:
    data = {
        "id": "sample-place",
        "name": "Sample Place",
        "activity_type": ["문화·역사"],
        "budget_level": ["low", "medium", "high"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon", "evening"],
        "area": "east-jeju",
        "duration_hours": 2,
        "priority": 7,
        "pace": ["easy", "tight"],
        "mobility": ["walkable"],
        "summary": "sample",
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


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


# --- pick_day_area (jeju day-area continuity) -------------------------------


def test_jeju_prefers_previous_day_area_or_its_neighbor_when_places_remain() -> None:
    # east-jeju와 인접(JEJU_AREA_NEIGHBORS)한 seongsan 둘 다 장소가 남아있으면,
    # preferred_areas 순서가 더 앞인 쪽이 뽑힌다.
    places = [
        build_place(id="a", area="east-jeju"),
        build_place(id="b", area="seongsan"),
        build_place(id="c", area="west-jeju"),  # 인접도 아니고, 더 선호돼도 뽑히면 안 됨
    ]
    preferred_areas = ["west-jeju", "seongsan", "east-jeju"]

    result = jeju_pick_day_area(
        preferred_areas, places, used_ids=set(), used_day_areas=set(), previous_day_area="east-jeju"
    )

    assert result == "seongsan"


def test_jeju_falls_back_to_the_only_remaining_candidate_among_previous_and_neighbor() -> None:
    # seongsan 쪽의 장소가 이미 다 쓰였으면(used_ids), west-jeju가 preferred_areas에서
    # 더 앞이어도 후보 집합(east-jeju, seongsan)에 없으니 무시하고 east-jeju가 뽑힌다.
    places = [
        build_place(id="a", area="east-jeju"),
        build_place(id="b", area="seongsan"),
        build_place(id="c", area="west-jeju"),
    ]
    preferred_areas = ["west-jeju", "seongsan", "east-jeju"]

    result = jeju_pick_day_area(
        preferred_areas, places, used_ids={"b"}, used_day_areas=set(), previous_day_area="east-jeju"
    )

    assert result == "east-jeju"


def test_jeju_pick_day_area_falls_back_to_none_when_no_candidate_area_has_places_left() -> None:
    # east-jeju/seongsan 둘 다 장소가 없으면(여기선 아예 그 권역 장소가 없음) None -
    # 호출부(RuleItineraryService._pick_day_area)가 기존 "아직 안 쓴 권역 우선" 로직으로
    # 폴백해야 한다는 신호.
    places = [build_place(id="c", area="west-jeju")]
    preferred_areas = ["west-jeju", "seongsan", "east-jeju"]

    result = jeju_pick_day_area(
        preferred_areas, places, used_ids=set(), used_day_areas=set(), previous_day_area="east-jeju"
    )

    assert result is None


def test_jeju_pick_day_area_is_unchanged_on_the_first_day() -> None:
    # 첫날(전날 권역 없음)은 연속성 규칙이 아예 개입하지 않는다 - 기존 로직 그대로.
    places = [build_place(id="a", area="east-jeju"), build_place(id="b", area="seongsan")]
    preferred_areas = ["seongsan", "east-jeju"]

    result = jeju_pick_day_area(
        preferred_areas, places, used_ids=set(), used_day_areas=set(), previous_day_area=None
    )

    assert result is None


def test_dispatcher_pick_day_area_never_overrides_seoul_or_busan() -> None:
    # neither seoul.py nor busan.py define pick_day_area, so the dispatcher
    # must return None regardless of previous_day_area - RuleItineraryService.
    # _pick_day_area then runs its existing fresh-area-first logic unchanged.
    places = [build_place(id="a", area="gangnam"), build_place(id="b", area="hongdae")]
    preferred_areas = ["hongdae", "gangnam"]

    for city in ("seoul", "busan"):
        request = build_request(city)
        result = pick_day_area(
            request, preferred_areas, places, used_ids=set(), used_day_areas=set(), previous_day_area="gangnam"
        )
        assert result is None, city
