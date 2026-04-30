import { useQuery } from "@tanstack/react-query";
import { getCommunityPlaces } from "../api/get-community-places";

type Params = {
  page: number;
  pageSize: number;
  keyword: string;
  city: string;
};

export function useCommunityPlacesQuery({ page, pageSize, keyword, city }: Params) {
  return useQuery({
    queryKey: ["community-places", page, pageSize, keyword, city],
    queryFn: () =>
      getCommunityPlaces({
        page,
        page_size: pageSize,
        q: keyword.trim() || undefined,
        city: city.trim() || undefined,
      }),
  });
}
