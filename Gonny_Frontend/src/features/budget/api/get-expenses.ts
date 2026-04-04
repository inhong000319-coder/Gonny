import { apiClient } from "../../../shared/api/client";
import { mockExpenses } from "../../../shared/mocks/trip-data";
import { Expense } from "../../../shared/types/domain";
import { ApiSuccessResponse } from "../../../shared/types/api";
import { ExpenseDto } from "../types/budget";

function mapExpense(dto: ExpenseDto, index: number): Expense {
  return {
    id: String(dto.expense_id ?? index),
    category: dto.category,
    amountLabel: `${(dto.amount_krw ?? dto.amount ?? 0).toLocaleString()} KRW`,
    note: dto.note,
  };
}

export async function getExpenses(tripId: string) {
  try {
    const response = await apiClient.get<ApiSuccessResponse<{ expenses: ExpenseDto[] }>>(
      `/trips/${tripId}/expenses`,
    );

    return response.data.data.expenses.map(mapExpense);
  } catch {
    return mockExpenses;
  }
}
