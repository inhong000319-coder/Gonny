import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { getTripReport } from "../api/get-trip-report";

export function useTripReportQuery(tripId: string) {
  return useQuery({
    queryKey: queryKeys.report(tripId),
    queryFn: () => getTripReport(tripId),
    enabled: Boolean(tripId),
  });
}
