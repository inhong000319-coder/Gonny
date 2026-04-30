import { useQuery } from "@tanstack/react-query";
import { getCommunityPlaceCities } from "../api/get-community-place-cities";

export function useCommunityPlaceCitiesQuery() {
  return useQuery({
    queryKey: ["community-place-cities"],
    queryFn: getCommunityPlaceCities,
  });
}
