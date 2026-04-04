import { BudgetOverview } from "../../../shared/types/domain";
import { BudgetGauge } from "./budget-gauge";

type BudgetSummaryCardProps = {
  budget: BudgetOverview;
};

export function BudgetSummaryCard({ budget }: BudgetSummaryCardProps) {
  return (
    <div className="card">
      <h2 className="section-title">예산</h2>
      <div className="page-grid" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>
        <div className="metric">
          <strong>총 예산</strong>
          <p>{budget.totalBudget.toLocaleString()}원</p>
        </div>
        <div className="metric">
          <strong>총 지출</strong>
          <p>{budget.totalSpent.toLocaleString()}원</p>
        </div>
        <div className="metric">
          <strong>잔여 예산</strong>
          <p>{budget.remainingBudget.toLocaleString()}원</p>
        </div>
      </div>
      <div style={{ marginTop: 16 }}>
        <BudgetGauge value={budget.usagePercent} />
      </div>
    </div>
  );
}
