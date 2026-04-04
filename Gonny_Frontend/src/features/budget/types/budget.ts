export type ExpenseDto = {
  expense_id?: number;
  category: string;
  amount?: number;
  amount_krw?: number;
  note: string;
};

export type ExpenseSummaryDto = {
  total_budget: number;
  total_spent: number;
  remaining: number;
  usage_pct: number;
  is_over_budget: boolean;
};
