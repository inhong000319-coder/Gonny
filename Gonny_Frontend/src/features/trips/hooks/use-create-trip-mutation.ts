import { useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { createTrip, CreateTripPayload } from "../api/create-trip";

export function useCreateTripMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateTripPayload) => createTrip(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.trips });
    },
  });
}
