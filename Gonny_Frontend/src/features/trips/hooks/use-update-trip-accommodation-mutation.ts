import { useMutation } from "@tanstack/react-query";
import { updateTripAccommodation } from "../api/update-trip-accommodation";

// #135 - stayIndex를 생략한 호출(기존 호출부 그대로)은 요청 본문에
// stay_index가 전혀 들어가지 않는다 - updateTripAccommodation 참고.
export function useUpdateTripAccommodationMutation(tripId: string) {
  return useMutation({
    mutationFn: (variables: { accommodationId: string | null; stayIndex?: number }) =>
      updateTripAccommodation(tripId, variables.accommodationId, variables.stayIndex),
  });
}
