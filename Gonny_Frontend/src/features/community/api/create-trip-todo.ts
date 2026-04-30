import { apiClient } from "../../../shared/api/client";
import { CreateTripTodoPayload, TripTodo } from "../types/community";

export async function createTripTodo(tripId: string, payload: CreateTripTodoPayload): Promise<TripTodo> {
  const response = await apiClient.post<TripTodo>(`/trips/${tripId}/community/todos`, payload);
  return response.data;
}
