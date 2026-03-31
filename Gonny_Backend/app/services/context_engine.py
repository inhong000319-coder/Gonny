"""Business logic for F03~F08 and F15."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Iterable, cast

from app.schemas.context import (
    AccommodationOption,
    AccommodationRecommendRequest,
    AccommodationRecommendResponse,
    AccommodationType,
    CuisineType,
    DurationEstimateRequest,
    DurationEstimateResponse,
    PreferenceTag,
    PreferenceMergeRequest,
    PreferenceMergeResponse,
    PreferenceWeight,
    RestaurantOption,
    RestaurantRecommendRequest,
    RestaurantRecommendResponse,
    SeasonalFeedItem,
    SeasonalFeedResponse,
    Season,
    SpotDurationResult,
    TransportLegPlan,
    TransportRecommendRequest,
    TransportRecommendResponse,
    WeatherAdjustmentItem,
    WeatherAdjustmentRequest,
    WeatherAdjustmentResponse,
    WeatherAlternative,
    WeatherForecastInput,
)


BASE_STAY_MINUTES = {
    "attraction": 90,
    "museum": 100,
    "restaurant": 60,
    "cafe": 45,
    "shopping": 80,
    "activity": 90,
    "nature": 100,
    "custom": 75,
}

TRANSPORT_SPEED_KMH = {
    "walk": 4.0,
    "public": 22.0,
    "car": 33.0,
    "mixed": 18.0,
}

ACCOMMODATION_SEED: list[tuple[str, AccommodationType, int, float, list[str], str]] = [
    ("Blue Coast Hotel", "hotel", 150000, 1.2, ["seaview", "breakfast"], "https://example.com/hotel/blue"),
    ("Namu Stay House", "guesthouse", 70000, 2.5, ["quiet", "kitchen"], "https://example.com/hotel/namu"),
    ("Harbor Pension", "pension", 130000, 3.2, ["family-room", "parking"], "https://example.com/hotel/harbor"),
    ("Skyline Resort", "resort", 230000, 4.0, ["pool", "kids-zone"], "https://example.com/hotel/skyline"),
    ("Urban Loft", "airbnb", 110000, 0.8, ["city-center", "self-checkin"], "https://example.com/hotel/urban"),
    ("Pine Camp", "camping", 60000, 5.5, ["nature", "bbq"], "https://example.com/hotel/pine"),
]

RESTAURANT_SEED: list[tuple[str, CuisineType, int, float, bool]] = [
    ("Hanok Kitchen", "korean", 18000, 4.5, True),
    ("Sunny Brunch Lab", "brunch", 22000, 4.4, False),
    ("Umi Sushi", "japanese", 26000, 4.6, True),
    ("Cloud Pasta", "western", 24000, 4.3, False),
    ("Green Bowl", "vegan", 17000, 4.7, False),
    ("Night Taproom", "pub", 30000, 4.2, True),
    ("Red Dragon", "chinese", 21000, 4.1, False),
]

PREFERENCE_TAG_SET: set[PreferenceTag] = {
    "food",
    "nature",
    "culture",
    "shopping",
    "healing",
    "activity",
}

SEASONAL_FEED = {
    "spring": [
        ("Cherry Blossom Drive", "Jinhae", "Peak blossom routes and walking trails", ["flower", "drive"]),
        ("Historic Bloom Tour", "Gyeongju", "Spring weather with heritage sites", ["culture", "spring"]),
        ("Weekend River Picnic", "Yeouido", "Easy one-day outdoor route", ["weekend", "city"]),
    ],
    "summer": [
        ("Beach + Cafe Route", "Gangneung", "Cool sea breeze and coastal cafes", ["beach", "cafe"]),
        ("Island Escape", "Jeju", "Water activities and sunset points", ["activity", "island"]),
        ("Family Valley Trip", "Gapyeong", "Shallow valley spots for kids", ["family", "nature"]),
    ],
    "autumn": [
        ("Foliage Mountain Day", "Seoraksan", "Best foliage timing and hikes", ["hiking", "leaf"]),
        ("Lakeside Bike Loop", "Nami Island", "Crisp weather bike route", ["bike", "scenic"]),
        ("Festival Weekend", "Andong", "Local food and cultural events", ["festival", "food"]),
    ],
    "winter": [
        ("Snow Festival Tour", "Hwacheon", "Ice festival and winter market", ["snow", "festival"]),
        ("Hot Spring Reset", "Asan", "Indoor-outdoor spa focused route", ["healing", "indoor"]),
        ("Ski + Cafe Combo", "Pyeongchang", "Slope + warm cafe day plan", ["ski", "activity"]),
    ],
}

WEATHER_INDOOR_ALTERNATIVES = [
    ("Modern Art Museum", "culture", "Indoor exhibit and weather-proof"),
    ("Local Cooking Class", "food", "Hands-on indoor local experience"),
    ("Large Indoor Market", "shopping", "Food and shopping in one stop"),
    ("Aquarium Walk", "family", "Child-friendly and fully indoor"),
    ("City Observatory", "viewpoint", "Indoor city view with elevator access"),
]


def _estimate_move_minutes(distance_km: float, mode: str) -> int:
    speed = TRANSPORT_SPEED_KMH.get(mode, TRANSPORT_SPEED_KMH["mixed"])
    hours = distance_km / speed
    minutes = max(5, round(hours * 60))
    return minutes


def estimate_duration(request: DurationEstimateRequest) -> DurationEstimateResponse:
    """F03: estimate stay + movement durations."""

    results: list[SpotDurationResult] = []
    total = 0

    for idx, spot in enumerate(request.spots):
        stay = spot.manual_duration_min or BASE_STAY_MINUTES[spot.category]
        move = 0 if idx == 0 else _estimate_move_minutes(request.avg_move_distance_km, request.transport_mode)
        slot_total = stay + move
        total += slot_total
        results.append(
            SpotDurationResult(
                name=spot.name,
                category=spot.category,
                stay_duration_min=stay,
                move_duration_min_from_previous=move,
                total_slot_duration_min=slot_total,
            )
        )

    warning = None
    if total > 600:
        warning = "Total estimated duration is above 10 hours. Consider reducing spots."

    return DurationEstimateResponse(spots=results, total_duration_min=total, warning=warning)


def build_weather_adjustments(
    request: WeatherAdjustmentRequest,
    live_forecasts: Iterable[WeatherForecastInput | dict[str, object]] | None = None,
) -> WeatherAdjustmentResponse:
    """F04: create weather alert + alternative recommendations."""

    source_forecasts: list[WeatherForecastInput] = list(request.forecasts)
    generated_from_live_weather = False

    if not source_forecasts and live_forecasts:
        generated_from_live_weather = True
        for item in live_forecasts:
            if isinstance(item, WeatherForecastInput):
                source_forecasts.append(item)
            else:
                source_forecasts.append(WeatherForecastInput.model_validate(item))

    adjustments: list[WeatherAdjustmentItem] = []
    for fc in source_forecasts:
        condition = fc.condition
        if condition not in {"rain", "snow"}:
            continue

        forecast_date = fc.forecast_date
        alternatives = [
            WeatherAlternative(title=title, category=category, reason=reason)
            for title, category, reason in WEATHER_INDOOR_ALTERNATIVES[:3]
        ]

        alert = (
            f"{forecast_date} has a {condition} forecast. "
            "Consider switching outdoor plans to indoor options."
        )
        adjustments.append(
            WeatherAdjustmentItem(
                forecast_date=forecast_date,
                condition=condition,
                alert_message=alert,
                alternatives=alternatives,
            )
        )

    return WeatherAdjustmentResponse(
        destination=request.destination,
        generated_from_live_weather=generated_from_live_weather,
        adjustments=adjustments,
    )


def merge_companion_preferences(request: PreferenceMergeRequest) -> PreferenceMergeResponse:
    """F05: merge companion tags with weighting."""

    counts: Counter[str] = Counter()
    for companion in request.companions:
        weight_boost = 2 if companion.is_child else 1
        for tag in companion.tags:
            counts[tag] += weight_boost

    for tag in request.base_trip_tags:
        counts[tag] += 1

    if not counts:
        counts.update({"healing": 1, "food": 1, "culture": 1})

    total = sum(counts.values())
    weighted = [
        PreferenceWeight(tag=cast(PreferenceTag, tag), weight_percent=round((value / total) * 100, 2))
        for tag, value in counts.most_common()
        if tag in PREFERENCE_TAG_SET
    ]

    top_tags = ", ".join([item.tag for item in weighted[:3]])
    summary = f"Top merged preferences: {top_tags}"
    return PreferenceMergeResponse(weights=weighted, summary=summary)


def recommend_accommodations(request: AccommodationRecommendRequest) -> AccommodationRecommendResponse:
    """F06: suggest accommodations by budget/type."""

    budget_bounds = {
        "value": (0, 100000),
        "mid": (90000, 180000),
        "premium": (170000, 400000),
    }
    min_budget, max_budget = budget_bounds[request.budget_level]

    preferred = set(request.preferred_types)
    selected: list[AccommodationOption] = []

    for name, acc_type, price, distance, highlights, url in ACCOMMODATION_SEED:
        if preferred and acc_type not in preferred:
            continue
        if price < min_budget or price > max_budget:
            continue
        selected.append(
            AccommodationOption(
                name=name,
                accommodation_type=acc_type,
                price_per_night_krw=price,
                distance_to_center_km=distance,
                highlights=highlights,
                booking_url=url,
            )
        )

    if not selected:
        selected = [
            AccommodationOption(
                name=name,
                accommodation_type=acc_type,
                price_per_night_krw=price,
                distance_to_center_km=distance,
                highlights=highlights,
                booking_url=url,
            )
            for name, acc_type, price, distance, highlights, url in ACCOMMODATION_SEED[:3]
        ]

    return AccommodationRecommendResponse(destination=request.destination, options=selected[:5])


def recommend_transport(
    request: TransportRecommendRequest,
    public_transit_overrides: dict[int, int] | None = None,
) -> TransportRecommendResponse:
    """F07: provide movement recommendations and duration estimates."""

    overrides = public_transit_overrides or {}
    plans: list[TransportLegPlan] = []
    total = 0

    for idx, leg in enumerate(request.legs):
        mode = request.transport_mode
        if mode == "mixed":
            if leg.distance_km <= 1.2:
                mode = "walk"
            elif leg.distance_km <= 20:
                mode = "public"
            else:
                mode = "car"

        if mode == "public" and idx in overrides:
            duration = overrides[idx]
        else:
            duration = _estimate_move_minutes(leg.distance_km, mode)

        note = None
        if duration > 30:
            note = "Long segment detected. Consider a break point."
        if mode == "car" and request.avoid_parking_difficult:
            note = "Parking-aware routing enabled. Favor easy parking zones."

        total += duration
        plans.append(
            TransportLegPlan(
                origin=leg.origin,
                destination=leg.destination,
                recommended_mode=mode,
                estimated_duration_min=duration,
                note=note,
            )
        )

    return TransportRecommendResponse(legs=plans, total_duration_min=total)


def recommend_restaurants(request: RestaurantRecommendRequest) -> RestaurantRecommendResponse:
    """F08: map meal slots to restaurant options."""

    preferred = set(request.preferred_cuisines)
    options: list[RestaurantOption] = []
    seed_idx = 0

    for slot in request.meal_slots:
        picked = None
        tries = 0
        while tries < len(RESTAURANT_SEED):
            row = RESTAURANT_SEED[seed_idx % len(RESTAURANT_SEED)]
            seed_idx += 1
            tries += 1
            if preferred and row[1] not in preferred:
                continue
            picked = row
            break

        if picked is None:
            picked = RESTAURANT_SEED[seed_idx % len(RESTAURANT_SEED)]
            seed_idx += 1

        name, cuisine, price, rating, needs_reservation = picked
        if request.budget_level == "value":
            price = max(8000, int(price * 0.85))
        elif request.budget_level == "premium":
            price = int(price * 1.25)

        if request.dietary_note and "vegan" in request.dietary_note.lower():
            cuisine = "vegan"
            name = "Green Bowl"
            price = 17000
            rating = 4.7
            needs_reservation = False

        options.append(
            RestaurantOption(
                day_label=slot.day_label,
                meal_type=slot.meal_type,
                name=name,
                cuisine=cuisine,
                estimated_price_krw=price,
                rating=rating,
                reservation_recommended=needs_reservation,
                map_url=f"https://maps.google.com/?q={name}",
            )
        )

    return RestaurantRecommendResponse(destination=request.destination, options=options)


def resolve_season(explicit_season: Season | None) -> Season:
    """Resolve season from explicit value or current month."""

    if explicit_season:
        return explicit_season

    month = date.today().month
    if month in {3, 4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    if month in {9, 10, 11}:
        return "autumn"
    return "winter"


def seasonal_feed(
    season: Season | None = None,
    destination: str | None = None,
    live_items: list[dict] | None = None,
) -> SeasonalFeedResponse:
    """F15: return seasonal destination feed."""

    final_season = resolve_season(season)

    if live_items:
        items = [
            SeasonalFeedItem(
                title=item["title"],
                region=item.get("region", "Unknown"),
                season=final_season,
                reason=item.get("reason", "Live API feed"),
                tags=item.get("tags", ["tour"]),
                source=item.get("source", "TourAPI"),
            )
            for item in live_items[:6]
        ]
        return SeasonalFeedResponse(
            season=final_season,
            destination=destination,
            generated_from_live_api=True,
            items=items,
        )

    items = [
        SeasonalFeedItem(
            title=title,
            region=region,
            season=final_season,
            reason=reason,
            tags=tags,
            source="seed",
        )
        for title, region, reason, tags in SEASONAL_FEED[final_season]
    ]

    if destination:
        destination_lower = destination.lower()
        filtered = [item for item in items if destination_lower in item.region.lower()]
        if filtered:
            items = filtered

    return SeasonalFeedResponse(
        season=final_season,
        destination=destination,
        generated_from_live_api=False,
        items=items,
    )
