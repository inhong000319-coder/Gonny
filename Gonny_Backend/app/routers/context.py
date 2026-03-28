"""Routes for travel context features owned by role B."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.settings import settings
from app.schemas.context import (
    AccommodationRecommendRequest,
    AccommodationRecommendResponse,
    DurationEstimateRequest,
    DurationEstimateResponse,
    PreferenceMergeRequest,
    PreferenceMergeResponse,
    RestaurantRecommendRequest,
    RestaurantRecommendResponse,
    Season,
    SeasonalFeedResponse,
    TransportRecommendRequest,
    TransportRecommendResponse,
    WeatherAdjustmentRequest,
    WeatherAdjustmentResponse,
)
from app.services.context_engine import (
    build_weather_adjustments,
    estimate_duration,
    merge_companion_preferences,
    recommend_accommodations,
    recommend_restaurants,
    recommend_transport,
    seasonal_feed,
)
from app.services.external_clients import ODSayClient, OpenWeatherClient, TourApiClient


router = APIRouter(prefix="/context", tags=["travel-context"])

openweather_client = OpenWeatherClient(settings)
tour_api_client = TourApiClient(settings)
odsay_client = ODSayClient(settings)


@router.post("/f03/duration-estimate", response_model=DurationEstimateResponse)
def f03_duration_estimate(payload: DurationEstimateRequest) -> DurationEstimateResponse:
    return estimate_duration(payload)


@router.post("/f04/weather-adjustments", response_model=WeatherAdjustmentResponse)
def f04_weather_adjustments(payload: WeatherAdjustmentRequest) -> WeatherAdjustmentResponse:
    live_forecasts = None
    if not payload.forecasts:
        live_forecasts = openweather_client.fetch_5day_forecast(payload.destination)
    return build_weather_adjustments(payload, live_forecasts=live_forecasts)


@router.post("/f05/merge-preferences", response_model=PreferenceMergeResponse)
def f05_merge_preferences(payload: PreferenceMergeRequest) -> PreferenceMergeResponse:
    return merge_companion_preferences(payload)


@router.post("/f06/accommodations", response_model=AccommodationRecommendResponse)
def f06_accommodations(payload: AccommodationRecommendRequest) -> AccommodationRecommendResponse:
    return recommend_accommodations(payload)


@router.post("/f07/transport", response_model=TransportRecommendResponse)
def f07_transport(payload: TransportRecommendRequest) -> TransportRecommendResponse:
    overrides: dict[int, int] = {}
    if payload.transport_mode == "public":
        for idx, leg in enumerate(payload.legs):
            has_coords = all(
                value is not None
                for value in [
                    leg.origin_lat,
                    leg.origin_lng,
                    leg.destination_lat,
                    leg.destination_lng,
                ]
            )
            if has_coords:
                duration = odsay_client.estimate_duration_min(
                    sx=leg.origin_lng,  # ODSay uses lng, lat for SX, SY
                    sy=leg.origin_lat,
                    ex=leg.destination_lng,
                    ey=leg.destination_lat,
                )
                if duration:
                    overrides[idx] = duration

    return recommend_transport(payload, public_transit_overrides=overrides)


@router.post("/f08/restaurants", response_model=RestaurantRecommendResponse)
def f08_restaurants(payload: RestaurantRecommendRequest) -> RestaurantRecommendResponse:
    return recommend_restaurants(payload)


@router.get("/f15/feed", response_model=SeasonalFeedResponse)
def f15_feed(
    season: Season | None = Query(default=None),
    destination: str | None = Query(default=None, max_length=80),
) -> SeasonalFeedResponse:
    live_rows = tour_api_client.fetch_season_feed(keyword=destination)
    return seasonal_feed(season=season, destination=destination, live_items=live_rows)

