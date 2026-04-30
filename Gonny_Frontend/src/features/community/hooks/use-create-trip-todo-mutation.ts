import { useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../shared/api/query-keys";
import { createTripTodo } from "../api/create-trip-todo";
import { CreateTripTodoPayload } from "../types/community";

export function useCreateTripTodoMutation(tripId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateTripTodoPayload) => createTripTodo(tripId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tripCommunity(tripId) });
    },
  });
}
