import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { getTripDetail } from "../api/get-trip-detail";

export function useTripDetailQuery(tripId: string) {
  return useQuery({
    queryKey: queryKeys.trip(tripId),
    queryFn: () => getTripDetail(tripId),
    enabled: Boolean(tripId),
  });
}
