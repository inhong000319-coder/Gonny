import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { getCommunityFeed } from "../api/get-community-feed";

export function useCommunityFeedQuery() {
  return useQuery({
    queryKey: queryKeys.communityFeed,
    queryFn: getCommunityFeed,
  });
}
