import { useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { updateTripTodo } from "../api/update-trip-todo";
import { UpdateTripTodoPayload } from "../types/community";

export function useUpdateTripTodoMutation(tripId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ todoId, payload }: { todoId: number; payload: UpdateTripTodoPayload }) =>
      updateTripTodo(tripId, todoId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tripCommunity(tripId) });
    },
  });
}
