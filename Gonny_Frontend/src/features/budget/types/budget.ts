export type ExpenseDto = {
  expense_id?: number;
  category: string;
  amount?: number;
  amount_krw?: number;
  note: string;
};

export type ExpenseSummaryDto = {
  total_budget: number;
  // 숙박 지출은 제외한 금액 - remaining/usage_pct/is_over_budget도 전부
  // 이 값 기준이다. 숙박 지출 합계는 lodging_spent로 따로 내려온다.
  total_spent: number;
  remaining: number;
  usage_pct: number;
  is_over_budget: boolean;
  lodging_spent?: number;
};
