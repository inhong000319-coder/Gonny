import { apiClient } from "../../../shared/api/client";
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

// 백엔드에 /trips/{tripId}/expenses 엔드포인트가 아직 없어 이 요청은
// 항상 실패한다. get-expense-summary.ts와 동일하게 실패를 그대로
// 던져 react-query가 data undefined 상태를 갖게 한다 - 가짜 지출
// 내역으로 조용히 폴백하지 않는다 (ExpenseList가 data undefined를
// "준비 중"으로 표시함).
export async function getExpenses(tripId: string) {
  const response = await apiClient.get<ApiSuccessResponse<{ expenses: ExpenseDto[] }>>(
    `/trips/${tripId}/expenses`,
  );

  return response.data.data.expenses.map(mapExpense);
}
