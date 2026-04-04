import { apiClient } from "../../../shared/api/client";
import { ApiSuccessResponse } from "../../../shared/types/api";

export type CreateExpensePayload = {
  category: string;
  amount: number;
  currency: string;
  note: string;
  spent_at: string;
};

export type CreateExpenseResponse = {
  expense_id: number;
  category: string;
  amount_krw: number;
  remaining_budget: number;
  budget_usage_pct: number;
};

export async function createExpense(tripId: string, payload: CreateExpensePayload) {
  const response = await apiClient.post<ApiSuccessResponse<CreateExpenseResponse>>(
    `/trips/${tripId}/expenses`,
    payload,
  );

  return response.data.data;
}
