import { useQuery } from "@tanstack/react-query";
import { getCommunityJournalDetail } from "../api/get-community-journal-detail";

export function useCommunityJournalDetailQuery(journalId: number | null) {
  return useQuery({
    queryKey: ["community-journal-detail", journalId],
    queryFn: () => getCommunityJournalDetail(journalId as number),
    enabled: journalId !== null,
  });
}
