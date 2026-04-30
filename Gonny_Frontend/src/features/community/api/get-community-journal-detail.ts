import { apiClient } from "../../../shared/api/client";
import { CommunityJournalDetailResponse } from "../types/community";

export async function getCommunityJournalDetail(journalId: number): Promise<CommunityJournalDetailResponse> {
  const response = await apiClient.get<CommunityJournalDetailResponse>(`/community-feed/journals/${journalId}`);
  return response.data;
}
