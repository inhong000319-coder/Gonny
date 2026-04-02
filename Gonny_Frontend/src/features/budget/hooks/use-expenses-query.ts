import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { getExpenses } from "../api/get-expenses";

export function useExpensesQuery(tripId: string) {
  return useQuery({
    queryKey: queryKeys.expenses(tripId),
    queryFn: () => getExpenses(tripId),
    enabled: Boolean(tripId),
  });
}
