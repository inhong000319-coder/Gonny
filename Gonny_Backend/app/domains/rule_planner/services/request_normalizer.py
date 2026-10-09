from __future__ import annotations

import re

from fastapi import HTTPException, status

from app.domains.rule_planner.schemas import NormalizedRuleRequest, RuleItineraryRequest

from .arrival_departure import has_any_usable_slot
from .constants import DEFAULT_CITY_BY_COUNTRY, DEFAULT_COMPANION, DEFAULT_CONCEPTS, DEFAULT_STYLE


def normalize_rule_request(request: RuleItineraryRequest) -> NormalizedRuleRequest:
    nights, days = normalize_duration(
        nights=request.nights,
        days=request.days,
        duration_label=request.duration_label,
    )
    if request.transport_by_day is not None and len(request.transport_by_day) != days:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"transport_by_day must have exactly {days} entries (one per day), "
                f"got {len(request.transport_by_day)}."
            ),
        )
    if not has_any_usable_slot(
        arrival_period=request.arrival_period,
        departure_period=request.departure_period,
        days=days,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="선택한 도착·출발 시간대로는 일정을 만들 수 없어요.",
        )
    concepts = request.concepts or DEFAULT_CONCEPTS
    style = request.style or DEFAULT_STYLE
    companion_type = request.companion_type or DEFAULT_COMPANION
    budget_band = normalize_budget(request.budget_value, request.budget_band)
    accommodation_budget_band = request.accommodation_budget_band or budget_band
    accommodation_types = list(dict.fromkeys(request.accommodation_types or []))

    continent = (request.continent or "asia").strip().lower()
    country = (request.country or "").strip().lower()
    city = (request.city or "").strip().lower()

    if not city and country:
        city = DEFAULT_CITY_BY_COUNTRY.get(country, "")
    if not city:
        city = "seoul"
    if not country:
        country = next(
            (country_name for country_name, mapped_city in DEFAULT_CITY_BY_COUNTRY.items() if mapped_city == city),
            "korea",
        )

    return NormalizedRuleRequest(
        continent=continent,
        country=country,
        city=city,
        travelers=request.travelers or 2,
        nights=nights,
        days=days,
        budget_band=budget_band,
        concepts=concepts,
        style=style,
        companion_type=companion_type,
        accommodation_budget_band=accommodation_budget_band,
        accommodation_types=accommodation_types,
        transport_by_day=request.transport_by_day,
        start_date=request.start_date,
        arrival_period=request.arrival_period,
        departure_period=request.departure_period,
        include_breakfast=request.include_breakfast,
    )


def normalize_duration(
    *,
    nights: int | None,
    days: int | None,
    duration_label: str | None,
) -> tuple[int, int]:
    if duration_label:
        match = re.search(r"(\d+)\D+(\d+)", duration_label)
        if match:
            return int(match.group(1)), int(match.group(2))

    if nights and days:
        return nights, days
    if nights and not days:
        return nights, nights + 1
    if days and not nights:
        return max(days - 1, 1), days
    return 2, 3


def normalize_budget(budget_value: int | None, budget_band: str | None) -> str:
    if budget_band:
        return budget_band
    if budget_value is None:
        return "medium"
    if budget_value < 100:
        return "low"
    if budget_value < 300:
        return "medium"
    return "high"
