import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { getExpenseSummary } from "../api/get-expense-summary";

export function useBudgetSummaryQuery(tripId: string) {
  return useQuery({
    queryKey: [...queryKeys.expenses(tripId), "summary"],
    queryFn: () => getExpenseSummary(tripId),
    enabled: Boolean(tripId),
  });
}
