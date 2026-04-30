import { useQuery } from "@tanstack/react-query";
import { getCommunityTopPlaces } from "../api/get-community-top-places";

export function useCommunityTopPlacesQuery() {
  return useQuery({
    queryKey: ["community-top-places"],
    queryFn: getCommunityTopPlaces,
  });
}
