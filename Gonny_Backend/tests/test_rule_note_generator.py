from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.place_catalog import PlaceData
from app.schemas.rule_itinerary import NormalizedRuleRequest
from app.domains.rule_planner.services.note_generator import RuleNoteContext, TemplateRuleNoteGenerator


def build_place(**overrides) -> PlaceData:
    data = {
        "id": "hamdeok-beach",
        "name": "Hamdeok Beach",
        "activity_type": ["relax", "nature"],
        "visual_feature": ["포토스팟"],
        "budget_level": ["low", "medium", "high"],
        "suitable_for": ["solo", "couple", "friend", "family"],
        "time_fit": ["morning", "afternoon"],
        "area": "east-jeju",
        "duration_hours": 2,
        "priority": 9,
        "pace": ["easy"],
        "mobility": ["taxi-needed", "nearby"],
        "summary": "바다를 가까이에서 느끼며 천천히 걷기 좋은 코스예요.",
        "mood_keywords": ["여유로운", "차분한"],
        "highlight_tags": ["해안 풍경", "사진 포인트"],
        "note_templates": [],
    }
    data.update(overrides)
    return PlaceData.model_validate(data)


def build_request(**overrides) -> NormalizedRuleRequest:
    data = {
        "continent": "asia",
        "country": "korea",
        "city": "jeju",
        "travelers": 2,
        "nights": 2,
        "days": 3,
        "budget_band": "medium",
        "concepts": ["relax", "nature"],
        "style": "easy",
        "companion_type": "couple",
    }
    data.update(overrides)
    return NormalizedRuleRequest.model_validate(data)


def test_template_rule_note_generator_returns_four_lines() -> None:
    generator = TemplateRuleNoteGenerator()
    context = RuleNoteContext(
        place=build_place(),
        request=build_request(),
        time_slot="morning",
        day_number=1,
        localized_place_name="함덕해수욕장",
        localized_area_name="제주 동부",
        day_area_name="제주 동부",
    )

    note = generator.generate(context)
    lines = note.splitlines()

    assert lines[0] == "함덕해수욕장, 오전 일정의 시작으로 넣기 좋아요!"
    assert len(lines) == 4
    assert lines[1].endswith("요.")
    assert lines[2] == "바다를 가까이에서 느끼며 천천히 걷기 좋은 코스예요."
    assert lines[3].endswith("요.")


def test_template_rule_note_generator_prefers_same_area_route_hint() -> None:
    generator = TemplateRuleNoteGenerator()
    context = RuleNoteContext(
        place=build_place(id="woljeongri"),
        request=build_request(companion_type="friend", budget_band="high"),
        time_slot="afternoon",
        day_number=1,
        localized_place_name="월정리해변",
        localized_area_name="제주 동부",
        day_area_name="제주 동부",
        previous_place_name="함덕해수욕장",
        previous_area_name="제주 동부",
    )

    note = generator.generate(context)

    assert "월정리해변, 오후 일정에 자연스럽게 넣기 좋아요!" in note
    assert "함덕해수욕장과 같은 권역" in note
    assert "친구" in note or "분위기" in note or "여유" in note


def _route_sentence(*, previous_place, current_place, request, previous_area_name="제주 동부", localized_area_name="제주 동부"):
    generator = TemplateRuleNoteGenerator()
    context = RuleNoteContext(
        place=current_place,
        request=request,
        time_slot="afternoon",
        day_number=1,
        localized_place_name="현재 장소",
        localized_area_name=localized_area_name,
        previous_place_name=previous_place.name,
        previous_area_name=previous_area_name,
        previous_place=previous_place,
    )
    return generator.generate(context)


# --- "같은 권역" 조사 (받침 유무/비한글 이름) ---------------------------------


def test_route_sentence_uses_gwa_for_a_final_consonant_name() -> None:
    # 스누피가든 - 든에 받침이 있어 "와(과)" -> "과"
    previous = build_place(id="snoopy-garden-jeju", name="스누피가든", latitude=None, longitude=None)
    current = build_place(id="cur", name="현재 장소", latitude=None, longitude=None)
    note = _route_sentence(previous_place=previous, current_place=current, request=build_request())
    assert "스누피가든과 같은 권역" in note


def test_route_sentence_uses_wa_for_a_no_final_consonant_name() -> None:
    # 섭지코지 - 지에 받침이 없어 "와(과)" -> "와"
    previous = build_place(id="seopjikoji", name="섭지코지", latitude=None, longitude=None)
    current = build_place(id="cur", name="현재 장소", latitude=None, longitude=None)
    note = _route_sentence(previous_place=previous, current_place=current, request=build_request())
    assert "섭지코지와 같은 권역" in note
    assert "섭지코지과" not in note


def test_route_sentence_buffers_an_english_ending_name_with_jjok() -> None:
    # "ARTE Museum Jeju"처럼 영문으로 끝나는 이름은 받침 유무를 철자만으로
    # 안정적으로 알 수 없으므로 고정 완충어 "쪽"을 붙여 "쪽과"로 고정한다.
    previous = build_place(id="arte-museum-jeju", name="ARTE Museum Jeju", latitude=None, longitude=None)
    current = build_place(id="cur", name="현재 장소", latitude=None, longitude=None)
    note = _route_sentence(previous_place=previous, current_place=current, request=build_request())
    assert "ARTE Museum Jeju 쪽과 같은 권역" in note


def test_route_sentence_buffers_a_digit_ending_name_with_jjok() -> None:
    previous = build_place(id="example-9-81", name="9.81 파크", latitude=None, longitude=None)
    current = build_place(id="cur", name="현재 장소", latitude=None, longitude=None)
    note = _route_sentence(previous_place=previous, current_place=current, request=build_request())
    # "크" ends with a Korean syllable (no final consonant) - no buffer needed.
    assert "9.81 파크와 같은 권역" in note


def test_route_sentence_handles_a_symbol_containing_korean_ending_name() -> None:
    previous = build_place(id="jeju-43-peace-park", name="제주4·3평화공원", latitude=None, longitude=None)
    current = build_place(id="cur", name="현재 장소", latitude=None, longitude=None)
    note = _route_sentence(previous_place=previous, current_place=current, request=build_request())
    # 원 has a final consonant -> "과", and resolves off the trailing
    # Hangul syllable even though the name contains "·" earlier.
    assert "제주4·3평화공원과 같은 권역" in note


# --- 제주 세부 구역 기반 "같은 권역" 판정 --------------------------------------


def test_jeju_same_zone_places_get_the_same_area_sentence_even_with_coordinates() -> None:
    # halla-arboretum(jeju-city 구역)과 같은 구역의 다른 장소 - 실제
    # ZONE_CENTERS 좌표를 그대로 사용해 같은 구역임을 확인한다.
    previous = build_place(
        id="halla-arboretum", name="한라수목원", area="east-jeju", latitude=33.511545, longitude=126.526385
    )
    current = build_place(id="cur", name="현재 장소", area="east-jeju", latitude=33.512, longitude=126.527)
    note = _route_sentence(previous_place=previous, current_place=current, request=build_request())
    assert "한라수목원과 같은 권역" in note


def test_jeju_different_zone_places_do_not_get_the_same_area_sentence_despite_same_area_label() -> None:
    # halla-arboretum(jeju-city 구역, 33.51/126.53)과 snoopy-garden-jeju
    # (dongbu 구역, 33.44/126.78) - 둘 다 area="east-jeju"이지만 구역은
    # 다르다(기존 area 라벨 비교만 썼다면 "같은 권역"이라고 잘못 말했을
    # 조합).
    previous = build_place(
        id="halla-arboretum", name="한라수목원", area="east-jeju", latitude=33.469586747, longitude=126.4932439937
    )
    current = build_place(
        id="snoopy-garden-jeju-cur",
        name="스누피가든",
        area="east-jeju",
        latitude=33.44337164886826,
        longitude=126.77860501008234,
    )
    note = _route_sentence(previous_place=previous, current_place=current, request=build_request())
    assert "같은 권역" not in note


def test_jeju_without_coordinates_falls_back_to_area_label_comparison() -> None:
    # 좌표가 없으면(둘 중 하나라도) 기존 area 라벨 비교로 돌아간다 -
    # area가 같으면 여전히 "같은 권역" 문장을 쓴다.
    previous = build_place(id="halla-arboretum", name="한라수목원", area="east-jeju", latitude=None, longitude=None)
    current = build_place(id="snoopy-garden-jeju", name="스누피가든", area="east-jeju", latitude=None, longitude=None)
    note = _route_sentence(previous_place=previous, current_place=current, request=build_request())
    assert "한라수목원과 같은 권역" in note


def test_seoul_route_sentence_uses_area_label_comparison_unaffected_by_jeju_zones() -> None:
    # 서울은 zone 로직 자체를 타지 않는다 - area 라벨 비교 그대로.
    previous = build_place(id="gyeongbokgung", name="경복궁", area="jongno", latitude=37.579617, longitude=126.977041)
    current = build_place(id="bukchon", name="북촌한옥마을", area="jongno", latitude=37.582, longitude=126.983)
    request = build_request(city="seoul", concepts=["culture"])
    note = _route_sentence(
        previous_place=previous, current_place=current, request=request,
        previous_area_name="종로", localized_area_name="종로",
    )
    assert "경복궁과 같은 권역" in note


def test_template_rule_note_generator_resolves_particles_in_note_template() -> None:
    generator = TemplateRuleNoteGenerator()
    place = build_place(
        id="hallim-park",
        note_templates=[
            "{place_name}은(는) 2일차 일정에서 {area} 권역 분위기를 더해주기 좋은 코스예요.",
        ],
    )
    context = RuleNoteContext(
        place=place,
        request=build_request(companion_type="family"),
        time_slot="afternoon",
        day_number=2,
        localized_place_name="한림공원",
        localized_area_name="제주 서부",
        day_area_name="제주 서부",
    )

    note = generator.generate(context)

    assert note.splitlines()[0] == "한림공원, 오후 일정에 자연스럽게 넣기 좋아요!"
    assert "한림공원은 2일차 일정에서 제주 서부 권역 분위기를 더해주기 좋은 코스예요." in note
