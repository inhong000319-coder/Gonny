import { apiClient } from "../../../shared/api/client";
import { CommunityFeedResponse } from "../types/community";

export async function getCommunityFeed(): Promise<CommunityFeedResponse> {
  const response = await apiClient.get<CommunityFeedResponse>("/community-feed");
  return response.data;
}
