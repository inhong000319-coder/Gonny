from fastapi import HTTPException

from app.providers.place_catalog.local_json_catalog import LocalJsonPlaceCatalogProvider
from app.schemas.rule_itinerary import RuleItineraryRequest
from app.services.rule_itinerary_service import RuleItineraryService


def test_rule_itinerary_request_accepts_activity_concept() -> None:
    request = RuleItineraryRequest(concepts=["activity", "food"])

    assert request.concepts == ["activity", "food"]


def test_local_catalog_preserves_overseas_data_in_storage() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    seoul = provider.get_city_catalog(continent="asia", country="korea", city="seoul")
    tokyo = provider.get_city_catalog(continent="asia", country="japan", city="tokyo")

    seoul_place_ids = {place.id for place in seoul.places}
    tokyo_place_ids = {place.id for place in tokyo.places}

    assert "lotte-world-adventure" in seoul_place_ids
    assert "e-land-hangang-cruise" in seoul_place_ids
    assert "tokyo-disneysea" in tokyo_place_ids


def test_phase_one_draft_places_are_loaded_in_korean_focus_cities() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    seoul = provider.get_city_catalog(continent="asia", country="korea", city="seoul")
    busan = provider.get_city_catalog(continent="asia", country="korea", city="busan")

    seoul_place_ids = {place.id for place in seoul.places}
    busan_place_ids = {place.id for place in busan.places}

    assert {"sewoon-plaza", "cheonggyecheon-museum", "seoul-forest", "s-factory"} <= seoul_place_ids
    assert {"myeongdong-cathedral", "bank-of-korea-money-museum"} <= seoul_place_ids
    assert {"songdo-beach", "amnam-park"} <= busan_place_ids


def test_phase_one_draft_places_include_refined_visit_metadata() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    seoul = provider.get_city_catalog(continent="asia", country="korea", city="seoul")
    busan = provider.get_city_catalog(continent="asia", country="korea", city="busan")

    seoul_places = {place.id: place for place in seoul.places}
    busan_places = {place.id: place for place in busan.places}

    assert seoul_places["seoul-forest"].official_url == "https://parks.seoul.go.kr/template/sub/seoulforest.do"
    assert seoul_places["myeongdong-cathedral"].official_url == "https://www.mdsd.or.kr/"
    assert seoul_places["bank-of-korea-money-museum"].official_url == "https://museum.bok.or.kr/"
    assert seoul_places["sewoon-plaza"].slot_bias["afternoon"] > 0
    assert seoul_places["s-factory"].slot_bias["afternoon"] > 0
    assert busan_places["songdo-beach"].slot_bias["evening"] > 0
    assert busan_places["amnam-park"].slot_bias["morning"] > 0


def test_phase_two_draft_places_are_loaded_with_key_metadata() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    seoul = provider.get_city_catalog(continent="asia", country="korea", city="seoul")
    jeju = provider.get_city_catalog(continent="asia", country="korea", city="jeju")

    seoul_places = {place.id: place for place in seoul.places}
    jeju_places = {place.id: place for place in jeju.places}

    assert {"heunginjimun-gate", "dongdaemun-shopping-town"} <= seoul_places.keys()
    assert {"war-memorial-korea", "itaewon-antique-furniture-street"} <= seoul_places.keys()
    assert {"namsan-cable-car", "namsan-park-trail"} <= seoul_places.keys()
    assert {"arte-museum-jeju", "jeju-glass-castle"} <= jeju_places.keys()

    assert seoul_places["war-memorial-korea"].official_url == "https://www.warmemo.or.kr/Eng/index"
    assert jeju_places["arte-museum-jeju"].official_url == "https://artemuseum.com/JEJU"
    assert seoul_places["dongdaemun-shopping-town"].slot_bias["evening"] > 0
    assert seoul_places["namsan-cable-car"].slot_bias["evening"] > 0
    assert jeju_places["arte-museum-jeju"].slot_bias["afternoon"] > 0
    assert jeju_places["jeju-glass-castle"].slot_bias["afternoon"] > 0


def test_phase_three_seoul_draft_places_fill_jamsil_and_yeouido() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    seoul = provider.get_city_catalog(continent="asia", country="korea", city="seoul")

    jamsil_places = {place.id: place for place in seoul.places if place.area == "jamsil"}
    yeouido_places = {place.id: place for place in seoul.places if place.area == "yeouido"}

    assert {"seoul-sky", "lotte-world-mall"} <= jamsil_places.keys()
    assert {"the-hyundai-seoul", "63-square"} <= yeouido_places.keys()
    assert len(jamsil_places) >= 4
    assert len(yeouido_places) >= 4

    assert jamsil_places["seoul-sky"].official_url == "https://seoulsky.lotteworld.com/eng/main/index.do"
    assert jamsil_places["lotte-world-mall"].slot_bias["afternoon"] > 0
    assert yeouido_places["the-hyundai-seoul"].official_url == "https://www.thehyundaiseoul.com/"
    assert yeouido_places["63-square"].official_url == "http://www.63.co.kr/en/"
    assert yeouido_places["63-square"].slot_bias["evening"] > 0


def test_phase_three_busan_draft_places_fill_gwangalli_and_haeundae() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    busan = provider.get_city_catalog(continent="asia", country="korea", city="busan")

    gwangalli_places = {place.id: place for place in busan.places if place.area == "gwangalli"}
    haeundae_places = {place.id: place for place in busan.places if place.area == "haeundae"}

    assert {"millac-the-market", "f1963"} <= gwangalli_places.keys()
    assert {"sea-life-busan-aquarium", "busan-x-the-sky"} <= haeundae_places.keys()
    assert len(gwangalli_places) >= 5
    assert len(haeundae_places) >= 6

    assert gwangalli_places["millac-the-market"].slot_bias["evening"] > 0
    assert gwangalli_places["f1963"].slot_bias["afternoon"] > 0
    assert haeundae_places["sea-life-busan-aquarium"].official_url == "https://www.visitsealife.com/busan/en/"
    assert haeundae_places["sea-life-busan-aquarium"].slot_bias["afternoon"] > 0
    assert haeundae_places["busan-x-the-sky"].official_url == "https://www.busanxthesky.com/"
    assert haeundae_places["busan-x-the-sky"].slot_bias["evening"] > 0


def test_phase_three_jeju_draft_places_fill_seogwipo_west_and_seongsan() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    jeju = provider.get_city_catalog(continent="asia", country="korea", city="jeju")

    seogwipo_west_places = {place.id: place for place in jeju.places if place.area == "seogwipo-west"}
    seongsan_places = {place.id: place for place in jeju.places if place.area == "seongsan"}

    assert {"yeomiji-botanical-garden", "jeju-teddy-bear-museum"} <= seogwipo_west_places.keys()
    assert {"gwangchigi-beach", "seongeup-folk-village"} <= seongsan_places.keys()
    assert len(seogwipo_west_places) >= 5
    assert len(seongsan_places) >= 5

    assert seogwipo_west_places["yeomiji-botanical-garden"].official_url == "https://www.yeomiji.or.kr/"
    assert seogwipo_west_places["yeomiji-botanical-garden"].slot_bias["afternoon"] > 0
    assert seogwipo_west_places["jeju-teddy-bear-museum"].slot_bias["afternoon"] > 0
    assert seongsan_places["gwangchigi-beach"].slot_bias["morning"] > 0
    assert seongsan_places["seongeup-folk-village"].slot_bias["afternoon"] > 0


def test_phase_four_seoul_draft_places_fill_hongdae_and_gangnam() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    seoul = provider.get_city_catalog(continent="asia", country="korea", city="seoul")

    hongdae_places = {place.id: place for place in seoul.places if place.area == "hongdae"}
    gangnam_places = {place.id: place for place in seoul.places if place.area == "gangnam"}

    assert {"ktng-sangsangmadang-hongdae", "trick-eye-museum-seoul"} <= hongdae_places.keys()
    assert {"bongeunsa-temple", "seonjeongneung"} <= gangnam_places.keys()
    assert len(hongdae_places) >= 5
    assert len(gangnam_places) >= 5

    assert hongdae_places["ktng-sangsangmadang-hongdae"].official_url == "https://www.sangsangmadang.com/"
    assert hongdae_places["trick-eye-museum-seoul"].slot_bias["afternoon"] > 0
    assert gangnam_places["bongeunsa-temple"].official_url == "http://www.bongeunsa.org/"
    assert gangnam_places["bongeunsa-temple"].slot_bias["morning"] > 0
    assert gangnam_places["seonjeongneung"].slot_bias["afternoon"] > 0


def test_phase_four_busan_draft_places_fill_nampo_and_songdo() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    busan = provider.get_city_catalog(continent="asia", country="korea", city="busan")

    nampo_places = {place.id: place for place in busan.places if place.area == "nampo"}
    songdo_places = {place.id: place for place in busan.places if place.area == "songdo"}

    assert {"yongdusan-park", "bosu-book-street"} <= nampo_places.keys()
    assert {"songdo-yonggung-suspension-bridge", "songdo-sky-park"} <= songdo_places.keys()
    assert len(nampo_places) >= 6
    assert len(songdo_places) >= 6

    assert nampo_places["yongdusan-park"].official_url == "https://www.bisco.or.kr/yongdusanpark/"
    assert nampo_places["yongdusan-park"].slot_bias["evening"] > 0
    assert nampo_places["bosu-book-street"].slot_bias["afternoon"] > 0
    assert songdo_places["songdo-yonggung-suspension-bridge"].slot_bias["afternoon"] > 0
    assert songdo_places["songdo-sky-park"].slot_bias["evening"] > 0


def test_phase_four_jeju_draft_places_fill_east_and_west_jeju() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    jeju = provider.get_city_catalog(continent="asia", country="korea", city="jeju")

    east_places = {place.id: place for place in jeju.places if place.area == "east-jeju"}
    west_places = {place.id: place for place in jeju.places if place.area == "west-jeju"}

    assert {"jeju-stone-park", "haenyeo-museum"} <= east_places.keys()
    assert {"9-81-park-jeju", "saebyeol-oreum"} <= west_places.keys()
    assert len(east_places) >= 7
    assert len(west_places) >= 7

    assert east_places["jeju-stone-park"].official_url == "https://jeju.go.kr/jejustonepark/index.htm"
    assert east_places["jeju-stone-park"].slot_bias["afternoon"] > 0
    assert east_places["haenyeo-museum"].official_url == "https://www.jeju.go.kr/haenyeo/index.htm"
    assert west_places["9-81-park-jeju"].official_url == "https://www.981park.com/"
    assert west_places["9-81-park-jeju"].slot_bias["afternoon"] > 0
    assert west_places["saebyeol-oreum"].slot_bias["evening"] > 0


def test_phase_five_seoul_draft_places_fill_euljiro_and_jamsil() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    seoul = provider.get_city_catalog(continent="asia", country="korea", city="seoul")

    euljiro_places = {place.id: place for place in seoul.places if place.area == "euljiro"}
    jamsil_places = {place.id: place for place in seoul.places if place.area == "jamsil"}

    assert {"euljiro-nogari-alley", "daelim-sangga"} <= euljiro_places.keys()
    assert {"lotte-world-aquarium", "seoul-baekje-museum"} <= jamsil_places.keys()
    assert len(euljiro_places) >= 5
    assert len(jamsil_places) >= 6

    assert euljiro_places["euljiro-nogari-alley"].slot_bias["evening"] > 0
    assert euljiro_places["daelim-sangga"].slot_bias["afternoon"] > 0
    assert jamsil_places["lotte-world-aquarium"].official_url == "https://aquarium.lotteworld.com/"
    assert jamsil_places["lotte-world-aquarium"].slot_bias["afternoon"] > 0
    assert jamsil_places["seoul-baekje-museum"].official_url == "https://baekjemuseum.seoul.go.kr/eng/"
    assert jamsil_places["seoul-baekje-museum"].slot_bias["afternoon"] > 0


def test_phase_six_seoul_draft_places_fill_hongdae_and_gangnam_second_wave() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    seoul = provider.get_city_catalog(continent="asia", country="korea", city="seoul")

    hongdae_places = {place.id: place for place in seoul.places if place.area == "hongdae"}
    gangnam_places = {place.id: place for place in seoul.places if place.area == "gangnam"}

    assert {"rolling-hall", "ak-plaza-hongdae"} <= hongdae_places.keys()
    assert {"hyundai-motorstudio-seoul", "kmca-seoul"} <= gangnam_places.keys()
    assert len(hongdae_places) >= 7
    assert len(gangnam_places) >= 7

    assert hongdae_places["rolling-hall"].slot_bias["evening"] > 0
    assert hongdae_places["ak-plaza-hongdae"].slot_bias["afternoon"] > 0
    assert gangnam_places["hyundai-motorstudio-seoul"].slot_bias["afternoon"] > 0
    assert gangnam_places["kmca-seoul"].slot_bias["afternoon"] > 0


def test_phase_seven_seoul_draft_places_fill_yeouido_second_wave() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    seoul = provider.get_city_catalog(continent="asia", country="korea", city="seoul")

    yeouido_places = {place.id: place for place in seoul.places if place.area == "yeouido"}

    assert {"kbs-hall", "sema-bunker"} <= yeouido_places.keys()
    assert len(yeouido_places) >= 6

    assert yeouido_places["kbs-hall"].slot_bias["evening"] > 0
    assert yeouido_places["sema-bunker"].slot_bias["afternoon"] > 0


def test_phase_eight_busan_draft_places_fill_nampo_second_wave() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    busan = provider.get_city_catalog(continent="asia", country="korea", city="busan")

    nampo_places = {place.id: place for place in busan.places if place.area == "nampo"}

    assert {"busan-tower", "busan-modern-history-museum"} <= nampo_places.keys()
    assert len(nampo_places) >= 8

    assert nampo_places["busan-tower"].slot_bias["evening"] > 0
    assert nampo_places["busan-modern-history-museum"].slot_bias["afternoon"] > 0


def test_phase_nine_busan_draft_places_fill_songdo_second_wave() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    busan = provider.get_city_catalog(continent="asia", country="korea", city="busan")

    songdo_places = {place.id: place for place in busan.places if place.area == "songdo"}

    assert {"busan-moca", "huinnyeoul-culture-village"} <= songdo_places.keys()
    assert len(songdo_places) >= 8

    assert songdo_places["busan-moca"].slot_bias["afternoon"] > 0
    assert songdo_places["huinnyeoul-culture-village"].slot_bias["evening"] > 0


def test_phase_ten_jeju_draft_places_fill_east_jeju_second_wave() -> None:
    provider = LocalJsonPlaceCatalogProvider()
    jeju = provider.get_city_catalog(continent="asia", country="korea", city="jeju")

    east_places = {place.id: place for place in jeju.places if place.area == "east-jeju"}

    assert {"snoopy-garden-jeju", "delmoondo-gimnyeong"} <= east_places.keys()
    assert len(east_places) >= 9

    assert east_places["snoopy-garden-jeju"].official_url == "https://www.snoopygarden.com/jeju"
    assert east_places["snoopy-garden-jeju"].slot_bias["afternoon"] > 0
    assert east_places["delmoondo-gimnyeong"].official_url == "https://www.delmoondo.com/service/company"
    assert east_places["delmoondo-gimnyeong"].slot_bias["afternoon"] > 0


def test_public_catalog_options_only_include_korean_focus_cities() -> None:
    service = RuleItineraryService()
    options = service.list_catalog_options()

    assert {option.city for option in options} == {"seoul", "busan", "jeju"}


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


def test_hidden_foreign_city_is_unavailable_in_rule_itinerary_service() -> None:
    service = RuleItineraryService()
    request = RuleItineraryRequest(
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

    try:
        service.generate(request)
    except HTTPException as error:
        assert error.status_code == 404
        assert error.detail == "Destination is currently unavailable."
    else:
        raise AssertionError("Expected hidden foreign city request to be rejected.")
