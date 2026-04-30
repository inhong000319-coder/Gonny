import { apiClient } from "../../../shared/api/client";
import { TripCommunityResponse } from "../types/community";

export async function getTripCommunity(tripId: string): Promise<TripCommunityResponse> {
  const response = await apiClient.get<TripCommunityResponse>(`/trips/${tripId}/community`);
  return response.data;
}
