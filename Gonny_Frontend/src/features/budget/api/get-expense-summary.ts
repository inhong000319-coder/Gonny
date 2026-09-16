import { apiClient } from "../../../shared/api/client";
import { BudgetOverview } from "../../../shared/types/domain";
import { ApiSuccessResponse } from "../../../shared/types/api";
import { ExpenseSummaryDto } from "../types/budget";

function mapBudgetSummary(dto: ExpenseSummaryDto): BudgetOverview {
  return {
    totalBudget: dto.total_budget,
    totalSpent: dto.total_spent,
    remainingBudget: dto.remaining,
    usagePercent: dto.usage_pct,
  };
}

// 백엔드에 /trips/{tripId}/expenses/summary 엔드포인트가 아직 없어 이
// 요청은 항상 실패한다. 실패를 그대로 던져 react-query의 isError/data
// undefined 상태를 활용한다 - 가짜 숫자로 조용히 폴백하지 않는다
// (BudgetSummaryCard가 data undefined를 "준비 중"으로 표시함).
export async function getExpenseSummary(tripId: string) {
  const response = await apiClient.get<ApiSuccessResponse<ExpenseSummaryDto>>(
    `/trips/${tripId}/expenses/summary`,
  );

  return mapBudgetSummary(response.data.data);
}
