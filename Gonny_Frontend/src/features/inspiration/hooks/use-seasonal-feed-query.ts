import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { getSeasonalFeed } from "../api/get-seasonal-feed";

export function useSeasonalFeedQuery() {
  return useQuery({
    queryKey: queryKeys.seasonalFeed,
    queryFn: getSeasonalFeed,
  });
}
