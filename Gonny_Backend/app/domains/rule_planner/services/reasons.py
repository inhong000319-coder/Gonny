"""Fact-based "why this place" tags for RuleItineraryItem/RuleMealRecommendation.

Every reason here is derived from data already on the request or the place
(PlaceData fields, the already-computed travel minute, the already-built
weather alert list, already-loaded community feedback) - never from the
rule-based scoring numbers themselves (slot_score/base_score and friends in
slot_scoring.py are not read here at all). See RuleReason's docstring.

Candidate-building (build_activity_reason_candidates/build_meal_reason_candidates)
and day-wide selection (select_day_reasons) are deliberately separate: a
place's full, priority-ordered candidate list has to be known before the
day-wide "don't repeat the same label more than twice" rule (see
select_day_reasons) can decide which candidates actually make the cut.
"""

from __future__ import annotations

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest, RuleReason

from .community_feedback import MIN_TOTAL_REVIEWS, PlaceFeedbackSignal
from .constants import COMPANION_LABEL_KO, CONCEPT_LABEL_KO, TIME_SLOT_LABEL_KO
from .travel_estimate import estimate_accommodation_transition_minutes

# 가정값: 실측 데이터 없이 "직전 장소/숙소에서 가깝다"고 느끼는 경계를 도보
# 기준 15분으로 둔다.
NEAR_PREVIOUS_MAX_MINUTES = 15

# 장소 하나에 붙는 근거는 최대 이 개수까지만 노출한다 (우선순위 a~i 순).
MAX_REASONS_PER_PLACE = 3

# 같은 label 문구가 하루 동안 이 횟수를 넘겨 반복되면(예: 전부 "취향과
# 맞아요"), 그 이후 장소에서는 다음 우선순위 근거로 대체한다. 가정값 - 몇
# 번까지가 "반복돼 보이는지"에 대한 측정 데이터는 없다.
MAX_LABEL_REPEATS_PER_DAY = 2

# 기존 slot_scoring.TRANSIT_SUBWAY_FRIENDLY_BONUS가 쓰는 것과 동일한
# mobility 값 - 새 판정 기준을 만들지 않고 그대로 재사용한다.
SUBWAY_FRIENDLY_MOBILITY_VALUE = "subway-friendly"

# base_score(legacy_base_score)가 이미 "쉬운/빡빡한 일정" 선호를 pace로
# 판정하는 스타일만 pace_fit 근거의 대상으로 삼는다 - near-stay/
# mobility-first는 그 함수에서도 pace가 아니라 mobility로 판정하므로(이미
# transit_friendly가 그 영역을 다룬다) 여기서 새로 만들지 않는다.
PACE_MATCHING_STYLES = {"easy", "tight"}


def _near_previous_reason(travel_minutes: int | None, *, accommodation_label: bool) -> RuleReason | None:
    if travel_minutes is None or travel_minutes > NEAR_PREVIOUS_MAX_MINUTES:
        return None
    label = f"숙소에서 {travel_minutes}분" if accommodation_label else f"직전 장소에서 {travel_minutes}분"
    return RuleReason(code="near_previous", label=label)


def _resolve_travel_reason(
    *,
    travel_minutes_from_previous: int | None,
    is_first_of_day: bool,
    accommodation: AccommodationData | None,
    place: PlaceData,
) -> RuleReason | None:
    """(a) in the spec's priority list. A day's first place (no previous
    itinerary place to measure from) only gets a travel-based reason when
    the accommodation's distance is actually known - never falls back to
    guessing."""
    if is_first_of_day:
        accommodation_minutes = estimate_accommodation_transition_minutes(accommodation, place)
        return _near_previous_reason(accommodation_minutes, accommodation_label=True)
    return _near_previous_reason(travel_minutes_from_previous, accommodation_label=False)


def build_activity_reason_candidates(
    place: PlaceData,
    *,
    request: NormalizedRuleRequest,
    time_slot: str,
    day_number: int,
    travel_minutes_from_previous: int | None,
    is_first_of_day: bool,
    accommodation: AccommodationData | None,
    is_rain_alert_day: bool,
    feedback_signal: PlaceFeedbackSignal | None,
) -> list[RuleReason]:
    """Every reason candidate that applies to this activity place, in the
    spec's a-i priority order - not yet capped to MAX_REASONS_PER_PLACE and
    not yet subject to the day-wide repeated-label rule (see
    select_day_reasons, which both of those belong to)."""
    candidates: list[RuleReason] = []

    travel_reason = _resolve_travel_reason(
        travel_minutes_from_previous=travel_minutes_from_previous,
        is_first_of_day=is_first_of_day,
        accommodation=accommodation,
        place=place,
    )
    if travel_reason is not None:
        candidates.append(travel_reason)

    day_mode = request.transport_by_day[day_number - 1] if request.transport_by_day else None
    if day_mode == "transit" and SUBWAY_FRIENDLY_MOBILITY_VALUE in place.mobility:
        candidates.append(RuleReason(code="transit_friendly", label="지하철로 가기 편해요"))

    matched_concept = next(
        (concept for concept in request.concepts if concept in place.concept_tags),
        None,
    )
    if matched_concept is not None:
        candidates.append(
            RuleReason(
                code="concept_match",
                label=f"선택하신 '{CONCEPT_LABEL_KO.get(matched_concept, matched_concept)}' 취향과 맞아요",
            )
        )

    if request.companion_type in place.suitable_for:
        candidates.append(
            RuleReason(
                code="companion_fit",
                label=f"{COMPANION_LABEL_KO[request.companion_type]} 여행에 잘 맞아요",
            )
        )

    if time_slot in place.time_fit:
        candidates.append(
            RuleReason(code="time_fit", label=f"{TIME_SLOT_LABEL_KO[time_slot]}에 가기 좋아요")
        )

    if request.style in PACE_MATCHING_STYLES and request.style in place.pace:
        candidates.append(RuleReason(code="pace_fit", label="원하신 여행 속도에 맞아요"))

    if request.budget_band in place.budget_level:
        candidates.append(RuleReason(code="budget_fit", label="예산 범위 안이에요"))

    if is_rain_alert_day and place.setting == "indoor":
        candidates.append(RuleReason(code="indoor_ok", label="비 소식이 있는 날에도 즐기기 좋아요"))

    if feedback_signal is not None and feedback_signal.review_count >= MIN_TOTAL_REVIEWS:
        candidates.append(RuleReason(code="community_good", label="방문객 후기가 좋은 곳이에요"))

    return candidates


def build_meal_reason_candidates(
    place: PlaceData,
    *,
    associated_time_slot: str,
    travel_minutes_from_previous: int | None,
    is_first_of_day: bool,
    accommodation: AccommodationData | None,
) -> list[RuleReason]:
    """Meals only ever get a travel-based reason and a meal-time-fit
    reason (reusing the "time_fit" code against the meal's conventional
    slot - breakfast~morning/lunch~afternoon/dinner~evening) - never
    concept/companion/pace/budget/weather/community, and never anything
    about opening hours (see RuleMealRecommendation.hours_unverified)."""
    candidates: list[RuleReason] = []

    travel_reason = _resolve_travel_reason(
        travel_minutes_from_previous=travel_minutes_from_previous,
        is_first_of_day=is_first_of_day,
        accommodation=accommodation,
        place=place,
    )
    if travel_reason is not None:
        candidates.append(travel_reason)

    if associated_time_slot in place.time_fit:
        candidates.append(
            RuleReason(code="time_fit", label=f"{TIME_SLOT_LABEL_KO[associated_time_slot]}에 가기 좋아요")
        )

    return candidates


def select_day_reasons(day_candidates: list[list[RuleReason]]) -> list[list[RuleReason]]:
    """Applies the day-wide rules on top of each place's already-priority-
    ordered candidate list, in day order (day_candidates[i] is place i's
    candidates, earliest place first):

    - at most MAX_REASONS_PER_PLACE per place
    - a label already used by MAX_LABEL_REPEATS_PER_DAY earlier places that
      day is skipped in favor of the next-priority candidate, so the same
      phrase doesn't show up on every place (see MAX_LABEL_REPEATS_PER_DAY).

    code-level dedup per place falls out for free: build_*_reason_candidates
    never emits the same code twice for one place.
    """
    label_counts: dict[str, int] = {}
    selected: list[list[RuleReason]] = []

    for candidates in day_candidates:
        chosen: list[RuleReason] = []
        for candidate in candidates:
            if len(chosen) >= MAX_REASONS_PER_PLACE:
                break
            if label_counts.get(candidate.label, 0) >= MAX_LABEL_REPEATS_PER_DAY:
                continue
            chosen.append(candidate)
            label_counts[candidate.label] = label_counts.get(candidate.label, 0) + 1
        selected.append(chosen)

    return selected
