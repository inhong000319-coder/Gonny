import { useQuery } from "@tanstack/react-query";
import { getCommunityJournals } from "../api/get-community-journals";

type Params = {
  page: number;
  pageSize: number;
  sort: "views" | "recommendations";
  keyword: string;
};

export function useCommunityJournalsQuery({ page, pageSize, sort, keyword }: Params) {
  return useQuery({
    queryKey: ["community-journals", page, pageSize, sort, keyword],
    queryFn: () =>
      getCommunityJournals({
        page,
        page_size: pageSize,
        sort,
        q: keyword.trim() || undefined,
      }),
  });
}
