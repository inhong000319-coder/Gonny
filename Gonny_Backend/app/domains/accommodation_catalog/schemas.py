from pydantic import BaseModel, ConfigDict, Field


class AccommodationData(BaseModel):
    id: str
    name: str
    city: str
    area: str
    latitude: float | None = None
    longitude: float | None = None
    content_id: str | None = None

    # TourAPI's lclsSystm2 label for contentTypeId=32 (호텔/콘도미니엄/
    # 펜션·민박/모텔/캠핑/호스텔) - see
    # ACCOMMODATION_TYPE_LABELS_BY_LCLS2 in external_clients.py. There is
    # no 에어비앤비 category: TourAPI only carries officially registered
    # tourism lodging businesses, not platform listings, so that type
    # can't be represented from this data source.
    accommodation_type: str

    # Only amenities TourAPI's detailIntro2 actually exposes as a
    # flag/text field - see extract_lodging_amenities() in
    # external_clients.py. Notably, TourAPI has no breakfast ("조식제공")
    # or pool ("수영장") field for lodging (verified against both
    # detailIntro2 and detailInfo2), so those never appear here even
    # though they're common amenities in practice.
    amenities: list[str] = Field(default_factory=list)

    # Same value vocabulary as destination_catalog.PlaceData.budget_level
    # (low/medium/high). TourAPI rarely gives an actual price, so this is
    # inferred from accommodation_type and scale (room count, whether it's
    # a branded/large-scale hotel) rather than read directly from the API -
    # budget_level_estimated marks that inference explicitly rather than
    # presenting it as sourced fact.
    budget_level: list[str] = Field(default_factory=list)
    budget_level_estimated: bool = True

    suitable_for: list[str] = Field(default_factory=list)

    # Raw TourAPI checkintime/checkouttime text, stored verbatim - same
    # principle as PlaceData.open_hours/closed_days: this is free-form
    # prose (e.g. "15:00" but also sometimes "익일 12:00"), not parsed.
    checkin_time: str | None = None
    checkout_time: str | None = None

    # Not populated in this round - reserved for a later, separate pass
    # (e.g. ocean view / city view / mountain view research).
    view: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class CityAccommodationCatalog(BaseModel):
    city: str
    accommodations: list[AccommodationData]

    model_config = ConfigDict(str_strip_whitespace=True)
