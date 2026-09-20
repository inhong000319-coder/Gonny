import { useQuery } from "@tanstack/react-query";
import { getSharedTrip } from "../api/get-shared-trip";

export function useSharedTripQuery(token: string) {
  return useQuery({
    queryKey: ["shared-trip", token],
    queryFn: () => getSharedTrip(token),
    enabled: Boolean(token),
    // An expired/unknown token is a definitive 404, not a transient
    // failure - retrying won't ever succeed, so don't delay the honest
    // "link invalid" state behind react-query's default retry/backoff.
    retry: false,
  });
}
