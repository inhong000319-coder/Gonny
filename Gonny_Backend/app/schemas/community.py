from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TravelJournalTodoCreate(BaseModel):
    content: str
    is_done: bool = False


class TravelJournalTodoResponse(BaseModel):
    id: int
    content: str
    is_done: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class TravelJournalCommentCreate(BaseModel):
    content: str


class TravelJournalCommentUpdate(BaseModel):
    content: str


class TravelJournalCommentResponse(BaseModel):
    id: int
    journal_id: int
    content: str
    author_id: str | None = None
    author_name: str | None = None
    author_role: str | None = None
    created_at: datetime
    updated_at: datetime
    reactions: list["TravelJournalCommentReactionResponse"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TravelJournalReactionCreate(BaseModel):
    reaction_type: str
    delta: int = 1


class TravelJournalReactionResponse(BaseModel):
    id: int
    journal_id: int
    reaction_type: str
    count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TravelJournalCommentReactionCreate(BaseModel):
    reaction_type: str
    delta: int = 1


class TravelJournalCommentReactionResponse(BaseModel):
    id: int
    comment_id: int
    reaction_type: str
    count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TripTodoCreate(BaseModel):
    content: str
    day_number: int = Field(default=1, ge=1)
    is_done: bool = False


class TripTodoUpdate(BaseModel):
    content: str | None = None
    day_number: int | None = Field(default=None, ge=1)
    is_done: bool | None = None


class TripTodoResponse(BaseModel):
    id: int
    trip_id: int
    content: str
    day_number: int
    is_done: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TravelJournalContentBlock(BaseModel):
    id: str
    type: Literal["text", "image"]
    text: str | None = None
    url: str | None = None
    caption: str | None = None
    layout: Literal["small", "medium", "large", "full"] | None = "large"
    aspect_ratio: Literal["square", "portrait", "landscape", "story"] | None = "landscape"
    overlay_text: str | None = None
    emoji: str | None = None
    crop_x: int = Field(default=50, ge=0, le=100)
    crop_y: int = Field(default=50, ge=0, le=100)
    crop_left: float = Field(default=0.0, ge=0.0, le=99.0)
    crop_top: float = Field(default=0.0, ge=0.0, le=99.0)
    crop_width: float = Field(default=100.0, ge=1.0, le=100.0)
    crop_height: float = Field(default=100.0, ge=1.0, le=100.0)
    width_percent: int = Field(default=100, ge=30, le=100)
    zoom: float = Field(default=1.0, ge=1.0, le=4.0)
    offset_x: float = Field(default=0.0, ge=-100.0, le=100.0)
    offset_y: float = Field(default=0.0, ge=-100.0, le=100.0)
    text_items: list[dict] = Field(default_factory=list)
    emoji_items: list[dict] = Field(default_factory=list)
    draw_items: list[dict] = Field(default_factory=list)


class TravelJournalCreate(BaseModel):
    title: str
    diary_text: str
    reflection_text: str | None = None
    content_blocks: list[TravelJournalContentBlock] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    overall_rating: int | None = Field(default=None, ge=1, le=5)
    share_with_community: bool = False


class TravelJournalUpdate(BaseModel):
    title: str | None = None
    diary_text: str | None = None
    reflection_text: str | None = None
    content_blocks: list[TravelJournalContentBlock] | None = None
    image_urls: list[str] | None = None
    overall_rating: int | None = Field(default=None, ge=1, le=5)
    share_with_community: bool | None = None


class TravelJournalResponse(BaseModel):
    id: int
    trip_id: int
    title: str
    diary_text: str
    reflection_text: str | None
    content_blocks: list[TravelJournalContentBlock]
    image_urls: list[str]
    overall_rating: int | None
    share_with_community: bool
    view_count: int
    created_at: datetime
    updated_at: datetime
    todos: list[TravelJournalTodoResponse]
    comments: list[TravelJournalCommentResponse]
    reactions: list[TravelJournalReactionResponse]

    model_config = ConfigDict(from_attributes=True)


class PlaceReviewCreate(BaseModel):
    city: str
    place_name: str
    place_id: str | None = None
    rating: int = Field(ge=1, le=5)
    visit_time_slot: str | None = None
    companion_type: str | None = None
    recommended: bool = True
    would_revisit: bool = True
    tags: list[str] = Field(default_factory=list)
    review_text: str
    journal_id: int | None = None


class PlaceReviewUpdate(BaseModel):
    city: str | None = None
    place_name: str | None = None
    place_id: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    visit_time_slot: str | None = None
    companion_type: str | None = None
    recommended: bool | None = None
    would_revisit: bool | None = None
    tags: list[str] | None = None
    review_text: str | None = None


class PlaceReviewResponse(BaseModel):
    id: int
    trip_id: int
    journal_id: int | None
    city: str
    place_id: str | None
    place_name: str
    rating: int
    visit_time_slot: str | None
    companion_type: str | None
    recommended: bool
    would_revisit: bool
    tags: list[str]
    review_text: str
    reactions: list["PlaceReviewReactionResponse"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlaceReviewReactionCreate(BaseModel):
    reaction_type: str
    delta: int = 1


class PlaceReviewReactionResponse(BaseModel):
    id: int
    review_id: int
    reaction_type: str
    count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlaceStatResponse(BaseModel):
    id: int
    city: str
    place_name: str
    place_id: str | None
    review_count: int
    average_rating: float
    recommendation_rate: float
    revisit_rate: float
    top_tags: list[str]
    slot_scores: dict[str, float]
    companion_scores: dict[str, float]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TripCommunityResponse(BaseModel):
    trip_todos: list[TripTodoResponse]
    journals: list[TravelJournalResponse]
    reviews: list[PlaceReviewResponse]
    place_stats: list[PlaceStatResponse]


class PlaceSuggestionResponse(BaseModel):
    place_name: str
    city: str | None = None
    review_count: int = 0
    average_rating: float | None = None


class TagSuggestionResponse(BaseModel):
    tag: str
    count: int


class CommunityFeedJournalResponse(BaseModel):
    id: int
    trip_id: int
    trip_title: str
    destination: str
    title: str
    diary_text: str
    reflection_text: str | None
    content_blocks: list[TravelJournalContentBlock] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    overall_rating: int | None
    view_count: int
    recommendation_count: int
    created_at: datetime
    reactions: list[TravelJournalReactionResponse]


class CommunityFeedReviewResponse(BaseModel):
    id: int
    trip_id: int
    trip_title: str
    destination: str
    city: str
    place_name: str
    rating: int
    visit_time_slot: str | None
    companion_type: str | None
    recommended: bool
    would_revisit: bool
    tags: list[str]
    review_text: str
    created_at: datetime


class CommunityFeedResponse(BaseModel):
    journals: list[CommunityFeedJournalResponse]
    reviews: list[CommunityFeedReviewResponse]


class CommunityFeedJournalListResponse(BaseModel):
    items: list[CommunityFeedJournalResponse]
    total: int
    page: int
    page_size: int


class CommunityPlaceCardResponse(BaseModel):
    id: int
    city: str
    place_name: str
    review_count: int
    average_rating: float
    top_tags: list[str]

    model_config = ConfigDict(from_attributes=True)


class CommunityPlaceReviewItemResponse(BaseModel):
    id: int
    trip_id: int
    trip_title: str
    destination: str
    city: str
    place_name: str
    rating: int
    visit_time_slot: str | None
    companion_type: str | None
    recommended: bool
    would_revisit: bool
    tags: list[str]
    review_text: str
    reactions: list[PlaceReviewReactionResponse]
    created_at: datetime


class CommunityPlaceDetailResponse(BaseModel):
    place: CommunityPlaceCardResponse
    reviews: list[CommunityPlaceReviewItemResponse]


class CommunityPlaceListResponse(BaseModel):
    items: list[CommunityPlaceCardResponse]
    total: int
    page: int
    page_size: int


class CommunityPlaceCityResponse(BaseModel):
    city: str
    review_count: int


class CommunityJournalDetailResponse(BaseModel):
    trip_title: str
    destination: str
    journal: TravelJournalResponse


class JournalImageUploadResponse(BaseModel):
    url: str


TravelJournalCommentResponse.model_rebuild()
PlaceReviewResponse.model_rebuild()
