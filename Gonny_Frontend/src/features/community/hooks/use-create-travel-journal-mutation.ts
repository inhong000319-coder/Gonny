import { useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { createTravelJournal } from "../api/create-travel-journal";
import { CreateTravelJournalPayload } from "../types/community";

export function useCreateTravelJournalMutation(tripId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateTravelJournalPayload) => createTravelJournal(tripId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tripCommunity(tripId) });
    },
  });
}
