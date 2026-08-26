from pydantic import BaseModel, ConfigDict, Field


ACTIVITY_TYPE_CODE_MAP = {
    "나이트라이프": "nightlife",
    "문화·역사": "culture",
    "미식": "food",
    "쇼핑": "shopping",
    "액티비티": "activity",
    "온천": "onsen",
    "자연·트레킹": "nature",
    "휴양·힐링": "relax",
}

VISUAL_FEATURE_CODE_MAP = {
    "포토스팟": "photo",
    "야경": "night_view",
}


class FeaturedVideoData(BaseModel):
    video_id: str
    title: str
    channel: str
    view_count_text: str
    published: str | None = None
    youtube_url: str | None = None
    embed_url: str | None = None
    thumbnail_url: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class PlaceData(BaseModel):
    id: str
    name: str
    activity_type: list[str]
    mood: list[str] = Field(default_factory=list)
    mood_evening_override: list[str] = Field(default_factory=list)
    visual_feature: list[str] = Field(default_factory=list)
    budget_level: list[str]
    suitable_for: list[str]
    time_fit: list[str]
    area: str
    duration_hours: int = Field(ge=1, le=12)
    priority: int = Field(ge=1, le=10)
    pace: list[str]
    mobility: list[str]
    summary: str
    latitude: float | None = None
    longitude: float | None = None
    content_id: str | None = None
    # Raw TourAPI usetime/restdate text, stored verbatim - these are
    # free-form prose (e.g. "09:00~18:00(입장마감 17:30)"), not a
    # structured schedule, so we don't attempt to parse them into a
    # per-weekday structure (accuracy can't be guaranteed for arbitrary
    # prose formats across venue types).
    open_hours: str | None = None
    closed_days: str | None = None
    official_url: str | None = None
    booking_hint: str | None = None
    is_active: bool = True
    mvp_tier: str = "standard"
    full_day_recommended: bool = False
    full_day_notes: dict[str, list[str]] = Field(default_factory=dict)
    slot_bias: dict[str, int] = Field(default_factory=dict)
    mood_keywords: list[str] = Field(default_factory=list)
    highlight_tags: list[str] = Field(default_factory=list)
    note_templates: list[str] = Field(default_factory=list)

    model_config = ConfigDict(str_strip_whitespace=True)

    @property
    def activity_type_codes(self) -> list[str]:
        return [ACTIVITY_TYPE_CODE_MAP.get(value, value) for value in self.activity_type]

    @property
    def concept_tags(self) -> list[str]:
        tags = [*self.activity_type_codes, *[VISUAL_FEATURE_CODE_MAP.get(value, value) for value in self.visual_feature]]
        deduped: list[str] = []
        for tag in tags:
            if tag and tag not in deduped:
                deduped.append(tag)
        return deduped


class CityPlaceCatalog(BaseModel):
    continent: str
    country: str
    city: str
    continent_label: str | None = None
    country_label: str | None = None
    city_label: str | None = None
    aliases: list[str] = Field(default_factory=list)
    default_days: int = 3
    featured_video: FeaturedVideoData | None = None
    places: list[PlaceData]

    model_config = ConfigDict(str_strip_whitespace=True)


class DestinationSummary(BaseModel):
    continent: str
    country: str
    city: str
    continent_label: str | None = None
    country_label: str | None = None
    city_label: str | None = None
    total_places: int
    active_places: int
    activity_places: int


class DestinationListResponse(BaseModel):
    destinations: list[DestinationSummary]


class UpdatePlaceActiveRequest(BaseModel):
    is_active: bool


class CreatePlaceRequest(PlaceData):
    model_config = ConfigDict(str_strip_whitespace=True)


class CreateDestinationRequest(BaseModel):
    continent: str
    country: str
    city: str
    continent_label: str | None = None
    country_label: str | None = None
    city_label: str | None = None
    aliases: list[str] = Field(default_factory=list)
    default_days: int = Field(default=3, ge=1, le=14)

    model_config = ConfigDict(str_strip_whitespace=True)


class CatalogCityOption(BaseModel):
    continent: str
    country: str
    city: str
    aliases: list[str]
