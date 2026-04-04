import { apiClient } from "../../../shared/api/client";
import { mockBudgetOverview } from "../../../shared/mocks/trip-data";
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

export async function getExpenseSummary(tripId: string) {
  try {
    const response = await apiClient.get<ApiSuccessResponse<ExpenseSummaryDto>>(
      `/trips/${tripId}/expenses/summary`,
    );

    return mapBudgetSummary(response.data.data);
  } catch {
    return mockBudgetOverview;
  }
}
