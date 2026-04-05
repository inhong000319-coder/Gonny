from app.providers.place_catalog.local_json_catalog import LocalJsonPlaceCatalogProvider
from app.schemas.rule_itinerary import RuleItineraryRequest
from app.services.rule_itinerary_service import RuleItineraryService


def test_rule_itinerary_request_accepts_activity_concept() -> None:
    request = RuleItineraryRequest(concepts=["activity", "food"])

    assert request.concepts == ["activity", "food"]


def test_local_catalog_includes_added_activity_places() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    seoul = provider.get_city_catalog(continent="asia", country="korea", city="seoul")
    tokyo = provider.get_city_catalog(continent="asia", country="japan", city="tokyo")

    place_ids = {place.id for place in seoul.places}
    tokyo_place_ids = {place.id for place in tokyo.places}

    assert "lotte-world-adventure" in place_ids
    assert "e-land-hangang-cruise" in place_ids
    assert "tokyo-disneysea" in tokyo_place_ids


def test_activity_concept_prefers_activity_places_in_middle_of_trip() -> None:
    service = RuleItineraryService()
    response = service.generate(
        RuleItineraryRequest(
            continent="asia",
            country="korea",
            city="seoul",
            nights=2,
            days=3,
            budget_band="medium",
            concepts=["activity"],
            style="easy",
            companion_type="friend",
        )
    )

    second_day = [item for item in response.items if item.day_number == 2]

    assert "activity" in [item.category for item in second_day]


def test_full_day_activity_fills_middle_day_for_seoul() -> None:
    service = RuleItineraryService()
    response = service.generate(
        RuleItineraryRequest(
            continent="asia",
            country="korea",
            city="seoul",
            nights=2,
            days=3,
            budget_band="medium",
            concepts=["activity"],
            style="easy",
            companion_type="friend",
        )
    )

    second_day = [item for item in response.items if item.day_number == 2]

    assert [item.time_slot for item in second_day] == ["morning", "afternoon", "evening"]
    assert {item.category for item in second_day} == {"activity"}


def test_arrival_day_avoids_activity_heavy_schedule_for_seoul() -> None:
    service = RuleItineraryService()
    response = service.generate(
        RuleItineraryRequest(
            continent="asia",
            country="korea",
            city="seoul",
            nights=2,
            days=3,
            budget_band="medium",
            concepts=["activity"],
            style="easy",
            companion_type="friend",
        )
    )

    first_day = [item for item in response.items if item.day_number == 1]

    assert "activity" not in [item.category for item in first_day]


def test_departure_day_avoids_activity_heavy_schedule_for_seoul() -> None:
    service = RuleItineraryService()
    response = service.generate(
        RuleItineraryRequest(
            continent="asia",
            country="korea",
            city="seoul",
            nights=2,
            days=3,
            budget_band="medium",
            concepts=["activity"],
            style="easy",
            companion_type="friend",
        )
    )

    last_day = [item for item in response.items if item.day_number == 3]

    assert "activity" not in [item.category for item in last_day]


def test_half_day_activity_time_bias_for_chiangmai() -> None:
    service = RuleItineraryService()
    response = service.generate(
        RuleItineraryRequest(
            continent="asia",
            country="thailand",
            city="chiangmai",
            nights=2,
            days=3,
            budget_band="medium",
            concepts=["activity"],
            style="easy",
            companion_type="friend",
        )
    )

    second_day = {item.time_slot: item.place_name for item in response.items if item.day_number == 2}

    assert second_day["morning"] == "치앙마이 셀라돈 워크숍"
    assert second_day["afternoon"] == "치앙마이 나이트 사파리"


def test_activity_places_are_exposed_as_activity_category_when_selected() -> None:
    service = RuleItineraryService()
    response = service.generate(
        RuleItineraryRequest(
            continent="asia",
            country="taiwan",
            city="taipei",
            nights=2,
            days=3,
            budget_band="medium",
            concepts=["activity"],
            style="easy",
            companion_type="friend",
        )
    )

    second_day = [item for item in response.items if item.day_number == 2]

    assert any(item.category == "activity" for item in second_day[:2])
