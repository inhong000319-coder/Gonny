from __future__ import annotations

import re

from app.domains.rule_planner.schemas import NormalizedRuleRequest, RuleItineraryRequest

from .constants import DEFAULT_CITY_BY_COUNTRY, DEFAULT_COMPANION, DEFAULT_CONCEPTS, DEFAULT_STYLE


def normalize_rule_request(request: RuleItineraryRequest) -> NormalizedRuleRequest:
    nights, days = normalize_duration(
        nights=request.nights,
        days=request.days,
        duration_label=request.duration_label,
    )
    concepts = request.concepts or DEFAULT_CONCEPTS
    style = request.style or DEFAULT_STYLE
    companion_type = request.companion_type or DEFAULT_COMPANION
    budget_band = normalize_budget(request.budget_value, request.budget_band)

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
