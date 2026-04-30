import { apiClient } from "../../../shared/api/client";
import { CommunityPlaceCard } from "../types/community";

export async function getCommunityTopPlaces(): Promise<CommunityPlaceCard[]> {
  const response = await apiClient.get<CommunityPlaceCard[]>("/community-feed/places/top");
  return response.data;
}
