import { useMutation } from "@tanstack/react-query";
import { updateTripAccommodation } from "../api/update-trip-accommodation";

export function useUpdateTripAccommodationMutation(tripId: string) {
  return useMutation({
    mutationFn: (accommodationId: string | null) => updateTripAccommodation(tripId, accommodationId),
  });
}
