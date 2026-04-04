import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { getTrips } from "../api/get-trips";

export function useTripsQuery() {
  return useQuery({
    queryKey: queryKeys.trips,
    queryFn: getTrips,
  });
}
