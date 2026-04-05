from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.place_catalog import PlaceData
from app.schemas.rule_itinerary import NormalizedRuleRequest
from app.services.rule_note_generator import RuleNoteContext, TemplateRuleNoteGenerator


def build_place(**overrides) -> PlaceData:
    data = {
        "id": "hamdeok-beach",
        "name": "Hamdeok Beach",
        "category": ["relax", "photo", "nature"],
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
        localized_area_name="제주 동쪽",
        day_area_name="제주 동쪽",
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
        localized_area_name="제주 동쪽",
        day_area_name="제주 동쪽",
        previous_place_name="함덕해수욕장",
        previous_area_name="제주 동쪽",
    )

    note = generator.generate(context)

    assert "월정리해변, 오후 일정에 자연스럽게 넣기 좋아요!" in note
    assert "함덕해수욕장과 같은 권역" in note
    assert "친구" in note or "분위기" in note or "여유" in note


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
        localized_area_name="제주 서쪽",
        day_area_name="제주 서쪽",
    )

    note = generator.generate(context)

    assert note.splitlines()[0] == "한림공원, 오후 일정에 자연스럽게 넣기 좋아요!"
    assert "한림공원은 2일차 일정에서 제주 서쪽 권역 분위기를 더해주기 좋은 코스예요." in note
