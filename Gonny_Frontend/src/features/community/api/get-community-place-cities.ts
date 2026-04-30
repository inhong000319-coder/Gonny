import { apiClient } from "../../../shared/api/client";
import { CommunityPlaceCity } from "../types/community";

export async function getCommunityPlaceCities(): Promise<CommunityPlaceCity[]> {
  const response = await apiClient.get<CommunityPlaceCity[]>("/community-feed/place-cities");
  return response.data;
}
