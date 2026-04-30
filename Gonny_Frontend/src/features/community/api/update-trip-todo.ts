import { apiClient } from "../../../shared/api/client";
import { TripTodo, UpdateTripTodoPayload } from "../types/community";

export async function updateTripTodo(
  tripId: string,
  todoId: number,
  payload: UpdateTripTodoPayload,
): Promise<TripTodo> {
  const response = await apiClient.patch<TripTodo>(`/trips/${tripId}/community/todos/${todoId}`, payload);
  return response.data;
}
