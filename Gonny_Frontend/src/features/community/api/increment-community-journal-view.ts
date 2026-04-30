import { apiClient } from "../../../shared/api/client";
import { CommunityFeedJournal } from "../types/community";

export async function incrementCommunityJournalView(journalId: number): Promise<CommunityFeedJournal> {
  const response = await apiClient.post<CommunityFeedJournal>(`/community-feed/journals/${journalId}/view`);
  return response.data;
}
