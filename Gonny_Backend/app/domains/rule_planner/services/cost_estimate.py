from collections.abc import Iterable

from app.domains.accommodation_catalog.schemas import AccommodationData
from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import RuleCostEstimate

# Admission cap for places with an unknown fee. Of the 32 catalog places with a
# confirmed paid fee, the median is 15,000 KRW and the 90th percentile is
# 30,000 KRW, so this is roughly the top-decile fee.
UNPRICED_PLACE_MAX_KRW = 30000


def estimate_trip_cost_range(
    places: Iterable[PlaceData],
    accommodation: AccommodationData | None,
    travelers: int,
    nights: int,
) -> RuleCostEstimate | None:
    unique_places = list({place.id: place for place in places}.values())

    min_krw = 0
    max_krw = 0
    priced_count = 0
    unpriced_count = 0
    for place in unique_places:
        if place.average_cost_krw is None:
            unpriced_count += 1
            max_krw += UNPRICED_PLACE_MAX_KRW * travelers
            continue
        priced_count += 1
        min_krw += place.average_cost_krw * travelers
        max_krw += place.average_cost_krw * travelers

    accommodation_included = accommodation is not None and accommodation.average_price_krw is not None
    if accommodation_included:
        stay_krw = accommodation.average_price_krw * nights
        min_krw += stay_krw
        max_krw += stay_krw

    if not unique_places and not accommodation_included:
        return None

    return RuleCostEstimate(
        min_krw=min_krw,
        max_krw=max_krw,
        priced_place_count=priced_count,
        unpriced_place_count=unpriced_count,
        accommodation_included=accommodation_included,
        nights=nights,
        travelers=travelers,
    )
