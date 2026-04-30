import { apiClient } from "../../../shared/api/client";
import { CreatePlaceReviewPayload, PlaceReview } from "../types/community";

export async function createPlaceReview(tripId: string, payload: CreatePlaceReviewPayload): Promise<PlaceReview> {
  const response = await apiClient.post<PlaceReview>(`/trips/${tripId}/community/reviews`, payload);
  return response.data;
}
