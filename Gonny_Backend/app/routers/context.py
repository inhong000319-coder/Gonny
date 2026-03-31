"""API routes aligned with AI_여행에이전트_API설계서_v1."""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, Field

from app.core.settings import settings
from app.schemas.context import (
    AccommodationRecommendRequest,
    AccommodationType,
    CompanionPreferenceInput,
    PreferenceTag,
    PreferenceMergeRequest,
    Season,
    WeatherAdjustmentRequest,
    WeatherCondition,
    WeatherForecastInput,
)
from app.services.context_engine import (
    build_weather_adjustments,
    merge_companion_preferences,
    recommend_accommodations,
    seasonal_feed,
)
from app.services.external_clients import OpenWeatherClient, TourApiClient


router = APIRouter(tags=["api-v1"])

openweather_client = OpenWeatherClient(settings)
tour_api_client = TourApiClient(settings)

# Lightweight in-memory companion store for contract-level behavior.
_COMPANION_STORE: dict[int, list[dict[str, Any]]] = {}
_COMPANION_SEQ: dict[int, int] = {}


class WeatherRecommendRequest(BaseModel):
    day_number: int = Field(..., ge=1, le=30)
    weather_condition: str = Field(..., min_length=1, max_length=20)


class CompanionRegisterInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    preference_tags: list[str] = Field(default_factory=list, max_length=6)
    is_child: bool = False


class CompanionRegisterRequest(BaseModel):
    companions: list[CompanionRegisterInput] = Field(..., min_length=1, max_length=4)


def _ok(data: Any, message: str = "성공") -> dict[str, Any]:
    return {"success": True, "data": data, "message": message}


def _season_from_query(value: str | None) -> Season | None:
    if value is None:
        return None
    mapping: dict[str, Season] = {
        "봄": "spring",
        "여름": "summer",
        "가을": "autumn",
        "겨울": "winter",
        "spring": "spring",
        "summer": "summer",
        "autumn": "autumn",
        "fall": "autumn",
        "winter": "winter",
    }
    return mapping.get(value.lower() if value.isascii() else value)


def _season_to_korean(value: Season) -> str:
    mapping = {"spring": "봄", "summer": "여름", "autumn": "가을", "winter": "겨울"}
    return mapping[value]


def _weather_to_korean(value: str) -> str:
    mapping = {"clear": "맑음", "cloudy": "흐림", "rain": "비", "snow": "눈"}
    return mapping.get(value, value)


def _weather_to_normalized(value: str) -> str:
    mapping = {
        "맑음": "clear",
        "흐림": "cloudy",
        "비": "rain",
        "눈": "snow",
        "clear": "clear",
        "cloudy": "cloudy",
        "rain": "rain",
        "snow": "snow",
    }
    return mapping.get(value.lower() if value.isascii() else value, "cloudy")


def _normalize_preference_tags(values: list[str]) -> list[PreferenceTag]:
    allowed = {"food", "nature", "culture", "shopping", "healing", "activity"}
    return [cast(PreferenceTag, tag) for tag in values if tag in allowed]


def _next_companion_id(trip_id: int) -> int:
    current = _COMPANION_SEQ.get(trip_id, 0) + 1
    _COMPANION_SEQ[trip_id] = current
    return current


@router.get("/weather/{destination}")
def get_weather_forecast(
    destination: str,
    start_date: date | None = Query(default=None),
) -> dict[str, Any]:
    rows = openweather_client.fetch_5day_forecast(destination)

    forecasts: list[dict[str, Any]] = []
    for row in rows:
        item_date = row["forecast_date"]
        if start_date and item_date < start_date:
            continue

        condition = row["condition"]
        forecasts.append(
            {
                "date": str(item_date),
                "condition": _weather_to_korean(condition),
                "temp_max": row["max_temp_c"],
                "temp_min": row["min_temp_c"],
                "precipitation": 0 if condition in {"clear", "cloudy"} else 12,
                "is_outdoor_ok": condition in {"clear", "cloudy"},
            }
        )

    return _ok({"destination": destination, "forecasts": forecasts})


@router.post("/trips/{trip_id}/weather-recommend")
def post_weather_recommend(
    trip_id: int = Path(..., ge=1),
    payload: WeatherRecommendRequest | None = None,
) -> dict[str, Any]:
    payload = payload or WeatherRecommendRequest(day_number=1, weather_condition="비")
    condition = cast(WeatherCondition, _weather_to_normalized(payload.weather_condition))

    adjusted = build_weather_adjustments(
        WeatherAdjustmentRequest(
            destination=f"trip-{trip_id}",
            forecasts=[
                WeatherForecastInput(
                    forecast_date=date.today(),
                    condition=condition,
                    min_temp_c=10,
                    max_temp_c=16,
                )
            ],
            plan_slots=[],
        )
    )

    alternatives: list[dict[str, Any]] = []
    if adjusted.adjustments:
        alternatives.append(
            {
                "title": "실내 대안 코스",
                "items": [
                    {"place_name": alt.title, "duration_min": 60}
                    for alt in adjusted.adjustments[0].alternatives
                ],
            }
        )

    return _ok(
        {
            "weather_alert": f"{payload.day_number}일차 {payload.weather_condition} 예보",
            "alternatives": alternatives,
        }
    )


@router.get("/trips/{trip_id}/accommodations")
def get_accommodations(
    trip_id: int = Path(..., ge=1),
    type: AccommodationType | None = Query(default=None),
    max_price: int | None = Query(default=None, ge=10000),
) -> dict[str, Any]:
    if max_price is None:
        budget_level = "mid"
    elif max_price <= 100000:
        budget_level = "value"
    elif max_price <= 180000:
        budget_level = "mid"
    else:
        budget_level = "premium"

    payload = AccommodationRecommendRequest(
        destination=f"trip-{trip_id}",
        nights=1,
        budget_level=budget_level,
        preferred_types=[type] if type else [],
        companions_count=2,
    )
    recommended = recommend_accommodations(payload)

    accommodations = []
    for idx, option in enumerate(recommended.options, start=1):
        if max_price is not None and option.price_per_night_krw > max_price:
            continue
        accommodations.append(
            {
                "id": idx,
                "name": option.name,
                "type": option.accommodation_type,
                "address": f"{recommended.destination} 추천 숙소 주소",
                "price_range": f"{max(10000, option.price_per_night_krw - 20000):,}~{option.price_per_night_krw + 20000:,}원/박",
                "features": option.highlights,
                "checkin_time": "15:00",
                "checkout_time": "11:00",
                "booking_url": option.booking_url,
                "lat": 33.45 + idx * 0.01,
                "lng": 126.56 + idx * 0.01,
            }
        )

    return _ok({"accommodations": accommodations})


@router.post("/trips/{trip_id}/companions")
def post_companions(
    payload: CompanionRegisterRequest,
    trip_id: int = Path(..., ge=1),
) -> dict[str, Any]:
    companions = _COMPANION_STORE.setdefault(trip_id, [])
    parsed_companions: list[CompanionPreferenceInput] = []

    for row in payload.companions:
        companion_id = _next_companion_id(trip_id)
        companions.append(
            {
                "id": companion_id,
                "name": row.name,
                "preference_tags": row.preference_tags,
                "is_child": row.is_child,
            }
        )
        parsed_companions.append(
            CompanionPreferenceInput(
                name=row.name,
                tags=_normalize_preference_tags(row.preference_tags),
                is_child=row.is_child,
            )
        )

    merged = merge_companion_preferences(
        PreferenceMergeRequest(companions=parsed_companions, base_trip_tags=[])
    )
    summary = f"동행자 {len(payload.companions)}명 취향 통합 완료 ({', '.join(w.tag for w in merged.weights[:3])})"

    return _ok({"companions_count": len(payload.companions), "summary": summary})


@router.get("/trips/{trip_id}/companions")
def get_companions(trip_id: int = Path(..., ge=1)) -> dict[str, Any]:
    return _ok({"companions": _COMPANION_STORE.get(trip_id, [])})


@router.delete("/trips/{trip_id}/companions/{companion_id}")
def delete_companion(
    trip_id: int = Path(..., ge=1),
    companion_id: int = Path(..., ge=1),
) -> dict[str, Any]:
    rows = _COMPANION_STORE.get(trip_id, [])
    _COMPANION_STORE[trip_id] = [row for row in rows if row["id"] != companion_id]
    return _ok({"deleted": True, "companion_id": companion_id})


@router.get("/seasons/recommend")
def get_season_recommend(season: str | None = Query(default=None)) -> dict[str, Any]:
    normalized = _season_from_query(season)
    live_rows = tour_api_client.fetch_season_feed(keyword=None)
    feed = seasonal_feed(season=normalized, destination=None, live_items=live_rows)

    season_kr = _season_to_korean(feed.season)
    recommendations = [
        {
            "destination": item.region,
            "theme": item.tags[0] if item.tags else "여행",
            "description": item.reason,
            "best_period": f"{season_kr} 추천 시기",
            "estimated_cost_range": "1박 2일 기준 15~25만원",
            "weather": "맑음 / 15°C",
            "thumbnail_url": "https://example.com/thumbnail.jpg",
        }
        for item in feed.items
    ]

    return _ok({"season": season_kr, "recommendations": recommendations})


@router.get("/seasons/festivals")
def get_season_festivals(
    month: int | None = Query(default=None, ge=1, le=12),
    region: str | None = Query(default=None, max_length=80),
) -> dict[str, Any]:
    target_month = month or date.today().month
    live_rows = tour_api_client.fetch_season_feed(keyword=region)

    festivals = []
    if live_rows:
        for row in live_rows[:6]:
            festivals.append(
                {
                    "name": row["title"],
                    "region": row["region"],
                    "start_date": f"2026-{target_month:02d}-01",
                    "end_date": f"2026-{target_month:02d}-10",
                    "category": "축제",
                    "description": row.get("reason", "지역 행사 정보"),
                    "homepage_url": "https://example.com/festival",
                }
            )
    else:
        festivals = [
            {
                "name": "진해 군항제",
                "region": "경남 창원",
                "start_date": f"2026-{target_month:02d}-01",
                "end_date": f"2026-{target_month:02d}-10",
                "category": "꽃 축제",
                "description": "국내 대표 계절 축제",
                "homepage_url": "https://example.com/festival",
            }
        ]

    if region:
        region_lower = region.lower()
        festivals = [item for item in festivals if region_lower in item["region"].lower()]

    return _ok({"month": target_month, "festivals": festivals})
