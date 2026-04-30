import { apiClient } from "../../../shared/api/client";
import { CommunityFeedJournalListResponse } from "../types/community";

type Params = {
  page?: number;
  page_size?: number;
  sort?: "views" | "recommendations";
  q?: string;
};

export async function getCommunityJournals(params: Params): Promise<CommunityFeedJournalListResponse> {
  const response = await apiClient.get<CommunityFeedJournalListResponse>("/community-feed/journals", { params });
  return response.data;
}
