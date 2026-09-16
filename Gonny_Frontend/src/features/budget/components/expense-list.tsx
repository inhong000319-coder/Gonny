import { Expense } from "../../../shared/types/domain";

type ExpenseListProps = {
  expenses: Expense[] | undefined;
};

export function ExpenseList({ expenses }: ExpenseListProps) {
  if (!expenses) {
    return (
      <div className="card">
        <h2 className="section-title">최근 지출</h2>
        <p className="section-subtitle" style={{ marginBottom: 0 }}>
          지출 내역을 준비 중입니다.
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="section-title">최근 지출</h2>
      <div className="stack">
        {expenses.map((expense) => (
          <div className="trip-card" key={expense.id}>
            <strong>{expense.category}</strong>
            <p className="section-subtitle" style={{ margin: "8px 0 0" }}>
              {expense.amountLabel} / {expense.note}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
