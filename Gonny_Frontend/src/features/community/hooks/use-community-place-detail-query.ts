import { useQuery } from "@tanstack/react-query";
import { getCommunityPlaceDetail } from "../api/get-community-place-detail";

export function useCommunityPlaceDetailQuery(placeId: number | null) {
  return useQuery({
    queryKey: ["community-place-detail", placeId],
    queryFn: () => getCommunityPlaceDetail(placeId as number),
    enabled: placeId !== null,
  });
}
