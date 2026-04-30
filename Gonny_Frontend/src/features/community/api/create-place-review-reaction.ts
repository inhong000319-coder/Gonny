import { apiClient } from "../../../shared/api/client";
import { CreatePlaceReviewReactionPayload, PlaceReviewReaction } from "../types/community";

export async function createPlaceReviewReaction(
  tripId: number,
  reviewId: number,
  payload: CreatePlaceReviewReactionPayload,
): Promise<PlaceReviewReaction | null> {
  const response = await apiClient.post<PlaceReviewReaction | null>(
    `/trips/${tripId}/community/reviews/${reviewId}/reactions`,
    payload,
  );
  return response.data;
}
