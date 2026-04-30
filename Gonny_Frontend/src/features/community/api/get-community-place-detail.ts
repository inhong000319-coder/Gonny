import { apiClient } from "../../../shared/api/client";
import { CommunityPlaceDetailResponse } from "../types/community";

export async function getCommunityPlaceDetail(placeId: number): Promise<CommunityPlaceDetailResponse> {
  const response = await apiClient.get<CommunityPlaceDetailResponse>(`/community-feed/places/${placeId}`);
  return response.data;
}
