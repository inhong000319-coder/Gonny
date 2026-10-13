from __future__ import annotations

from app.domains.rule_planner.services.korean_particles import has_final_consonant, resolve_particles


def test_has_final_consonant_true_for_consonant_ending_syllable() -> None:
    assert has_final_consonant("스누피가든") is True  # 든 has a final consonant (ㄴ)


def test_has_final_consonant_false_for_vowel_ending_syllable() -> None:
    assert has_final_consonant("섭지코지") is False  # 지 has no final consonant


def test_has_final_consonant_false_for_non_korean_and_empty() -> None:
    assert has_final_consonant("ARTE Museum Jeju") is False
    assert has_final_consonant("") is False


def test_resolve_particles_topic_marker() -> None:
    assert resolve_particles("스누피가든은(는) 좋아요") == "스누피가든은 좋아요"
    assert resolve_particles("섭지코지은(는) 좋아요") == "섭지코지는 좋아요"


def test_resolve_particles_and_marker() -> None:
    assert resolve_particles("스누피가든와(과) 같은 권역") == "스누피가든과 같은 권역"
    assert resolve_particles("섭지코지와(과) 같은 권역") == "섭지코지와 같은 권역"


def test_resolve_particles_subject_and_object_markers() -> None:
    assert resolve_particles("스누피가든이(가) 있어요") == "스누피가든이 있어요"
    assert resolve_particles("섭지코지이(가) 있어요") == "섭지코지가 있어요"
    assert resolve_particles("스누피가든을(를) 봐요") == "스누피가든을 봐요"
    assert resolve_particles("섭지코지을(를) 봐요") == "섭지코지를 봐요"


def test_resolve_particles_leaves_ascii_ending_names_in_the_vowel_form() -> None:
    # Latin-script endings can't be reliably mapped to a Korean final
    # consonant from spelling alone - this module always picks the
    # no-final-consonant form rather than guess (callers that need a
    # guaranteed-correct result should avoid attaching the marker
    # directly to such a name - see note_generator._route_sentence_subject).
    assert resolve_particles("ARTE Museum Jeju와(과) 같은 권역") == "ARTE Museum Jeju와 같은 권역"


def test_resolve_particles_leaves_unmatched_marker_untouched() -> None:
    # Nothing matches [가-힣A-Za-z0-9] immediately before the marker.
    assert resolve_particles("'와(과)' 모양") == "'와(과)' 모양"
