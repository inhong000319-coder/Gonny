from pydantic import BaseModel, ConfigDict, Field


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
    category: list[str]
    budget_level: list[str]
    suitable_for: list[str]
    time_fit: list[str]
    area: str
    duration_hours: int = Field(ge=1, le=12)
    priority: int = Field(ge=1, le=10)
    pace: list[str]
    mobility: list[str]
    summary: str
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


class CityPlaceCatalog(BaseModel):
    continent: str
    country: str
    city: str
    aliases: list[str] = []
    default_days: int = 3
    featured_video: FeaturedVideoData | None = None
    places: list[PlaceData]

    model_config = ConfigDict(str_strip_whitespace=True)
