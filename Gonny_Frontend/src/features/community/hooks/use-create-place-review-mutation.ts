import { useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { createPlaceReview } from "../api/create-place-review";
import { CreatePlaceReviewPayload } from "../types/community";

export function useCreatePlaceReviewMutation(tripId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreatePlaceReviewPayload) => createPlaceReview(tripId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tripCommunity(tripId) });
    },
  });
}
