export type TravelJournalCommentReaction = {
  id: number;
  comment_id: number;
  reaction_type: string;
  count: number;
  created_at: string;
  updated_at: string;
};

export type TravelJournalComment = {
  id: number;
  journal_id: number;
  content: string;
  author_id: string | null;
  author_name: string | null;
  author_role: string | null;
  created_at: string;
  updated_at: string;
  reactions: TravelJournalCommentReaction[];
};

export type TravelJournalReaction = {
  id: number;
  journal_id: number;
  reaction_type: string;
  count: number;
  created_at: string;
  updated_at: string;
};

export type TripTodo = {
  id: number;
  trip_id: number;
  content: string;
  day_number: number;
  is_done: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type TravelJournalTodo = {
  id: number;
  content: string;
  is_done: boolean;
  sort_order: number;
};

export type TravelJournalContentBlock = {
  id: string;
  type: "text" | "image";
  text?: string | null;
  url?: string | null;
  caption?: string | null;
  layout?: "small" | "medium" | "large" | "full" | null;
  aspect_ratio?: "square" | "portrait" | "landscape" | "story" | null;
  overlay_text?: string | null;
  emoji?: string | null;
  crop_x?: number | null;
  crop_y?: number | null;
  crop_left?: number | null;
  crop_top?: number | null;
  crop_width?: number | null;
  crop_height?: number | null;
  width_percent?: number | null;
  zoom?: number | null;
  offset_x?: number | null;
  offset_y?: number | null;
  text_items?: Array<{ id: string; text: string; x: number; y: number; size?: number; rotation?: number; color?: string }>;
  emoji_items?: Array<{ id: string; emoji: string; x: number; y: number; size?: number; rotation?: number; color?: string }>;
  draw_items?: Array<{ id: string; color: string; size: number; points: Array<{ x: number; y: number }> }>;
};

export type TravelJournal = {
  id: number;
  trip_id: number;
  title: string;
  diary_text: string;
  reflection_text: string | null;
  content_blocks: TravelJournalContentBlock[];
  image_urls: string[];
  overall_rating: number | null;
  share_with_community: boolean;
  view_count: number;
  created_at: string;
  updated_at: string;
  todos: TravelJournalTodo[];
  comments: TravelJournalComment[];
  reactions: TravelJournalReaction[];
};

export type PlaceReview = {
  id: number;
  trip_id: number;
  journal_id: number | null;
  city: string;
  place_id: string | null;
  place_name: string;
  rating: number;
  visit_time_slot: string | null;
  companion_type: string | null;
  recommended: boolean;
  would_revisit: boolean;
  tags: string[];
  review_text: string;
  reactions: PlaceReviewReaction[];
  created_at: string;
  updated_at: string;
};

export type PlaceReviewReaction = {
  id: number;
  review_id: number;
  reaction_type: string;
  count: number;
  created_at: string;
  updated_at: string;
};

export type PlaceStat = {
  id: number;
  city: string;
  place_name: string;
  place_id: string | null;
  review_count: number;
  average_rating: number;
  recommendation_rate: number;
  revisit_rate: number;
  top_tags: string[];
  slot_scores: Record<string, number>;
  companion_scores: Record<string, number>;
  updated_at: string;
};

export type TripCommunityResponse = {
  trip_todos: TripTodo[];
  journals: TravelJournal[];
  reviews: PlaceReview[];
  place_stats: PlaceStat[];
};

export type CreateTripTodoPayload = {
  content: string;
  day_number: number;
  is_done?: boolean;
};

export type UpdateTripTodoPayload = {
  content?: string;
  day_number?: number;
  is_done?: boolean;
};

export type CreateTravelJournalPayload = {
  title: string;
  diary_text: string;
  reflection_text?: string | null;
  content_blocks?: TravelJournalContentBlock[];
  image_urls?: string[];
  overall_rating?: number | null;
  share_with_community: boolean;
};

export type UpdateTravelJournalPayload = Partial<CreateTravelJournalPayload>;

export type CreateTravelJournalCommentPayload = {
  content: string;
};

export type UpdateTravelJournalCommentPayload = {
  content: string;
};

export type CreateTravelJournalReactionPayload = {
  reaction_type: string;
  delta?: number;
};

export type CreateTravelJournalCommentReactionPayload = {
  reaction_type: string;
  delta?: number;
};

export type CreatePlaceReviewPayload = {
  city: string;
  place_name: string;
  place_id?: string | null;
  rating: number;
  visit_time_slot?: string | null;
  companion_type?: string | null;
  recommended: boolean;
  would_revisit: boolean;
  tags: string[];
  review_text: string;
  journal_id?: number | null;
};

export type UpdatePlaceReviewPayload = Partial<CreatePlaceReviewPayload>;

export type CreatePlaceReviewReactionPayload = {
  reaction_type: string;
  delta?: number;
};

export type PlaceSuggestion = {
  place_name: string;
  city: string | null;
  review_count: number;
  average_rating: number | null;
};

export type TagSuggestion = {
  tag: string;
  count: number;
};

export type CommunityFeedJournal = {
  id: number;
  trip_id: number;
  trip_title: string;
  destination: string;
  title: string;
  diary_text: string;
  reflection_text: string | null;
  content_blocks: TravelJournalContentBlock[];
  image_urls: string[];
  overall_rating: number | null;
  view_count: number;
  recommendation_count: number;
  created_at: string;
  reactions: TravelJournalReaction[];
};

export type CommunityFeedReview = {
  id: number;
  trip_id: number;
  trip_title: string;
  destination: string;
  city: string;
  place_name: string;
  rating: number;
  visit_time_slot: string | null;
  companion_type: string | null;
  recommended: boolean;
  would_revisit: boolean;
  tags: string[];
  review_text: string;
  created_at: string;
};

export type CommunityFeedResponse = {
  journals: CommunityFeedJournal[];
  reviews: CommunityFeedReview[];
};

export type CommunityFeedJournalListResponse = {
  items: CommunityFeedJournal[];
  total: number;
  page: number;
  page_size: number;
};

export type CommunityPlaceCard = {
  id: number;
  city: string;
  place_name: string;
  review_count: number;
  average_rating: number;
  top_tags: string[];
};

export type CommunityPlaceReviewItem = {
  id: number;
  trip_id: number;
  trip_title: string;
  destination: string;
  city: string;
  place_name: string;
  rating: number;
  visit_time_slot: string | null;
  companion_type: string | null;
  recommended: boolean;
  would_revisit: boolean;
  tags: string[];
  review_text: string;
  reactions: PlaceReviewReaction[];
  created_at: string;
};

export type CommunityPlaceDetailResponse = {
  place: CommunityPlaceCard;
  reviews: CommunityPlaceReviewItem[];
};

export type CommunityPlaceListResponse = {
  items: CommunityPlaceCard[];
  total: number;
  page: number;
  page_size: number;
};

export type CommunityPlaceCity = {
  city: string;
  review_count: number;
};

export type CommunityJournalDetailResponse = {
  trip_title: string;
  destination: string;
  journal: TravelJournal;
};

export type JournalImageUploadResponse = {
  url: string;
};
