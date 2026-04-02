import { useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { createExpense, CreateExpensePayload } from "../api/create-expense";

export function useCreateExpenseMutation(tripId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateExpensePayload) => createExpense(tripId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.expenses(tripId) });
      queryClient.invalidateQueries({ queryKey: [...queryKeys.expenses(tripId), "summary"] });
    },
  });
}
