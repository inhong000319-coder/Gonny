import { apiClient } from "../../../shared/api/client";
import { CommunityPlaceListResponse } from "../types/community";

type Params = {
  page?: number;
  page_size?: number;
  q?: string;
  city?: string;
};

export async function getCommunityPlaces(params: Params): Promise<CommunityPlaceListResponse> {
  const response = await apiClient.get<CommunityPlaceListResponse>("/community-feed/places", { params });
  return response.data;
}
