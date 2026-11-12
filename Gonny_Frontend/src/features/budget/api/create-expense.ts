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
  // 숙박 지출은 제외한 금액 기준.
  remaining_budget: number;
  budget_usage_pct: number;
  // 숙박 지출 합계(참고용) - remaining_budget/budget_usage_pct에는 포함되지 않는다.
  lodging_spent?: number;
};

export async function createExpense(tripId: string, payload: CreateExpensePayload) {
  const response = await apiClient.post<ApiSuccessResponse<CreateExpenseResponse>>(
    `/trips/${tripId}/expenses`,
    payload,
  );

  return response.data.data;
}
