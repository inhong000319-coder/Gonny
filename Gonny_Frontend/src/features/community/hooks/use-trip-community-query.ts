import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { getTripCommunity } from "../api/get-trip-community";

export function useTripCommunityQuery(tripId: string) {
  return useQuery({
    queryKey: queryKeys.tripCommunity(tripId),
    queryFn: () => getTripCommunity(tripId),
    enabled: Boolean(tripId),
  });
}
