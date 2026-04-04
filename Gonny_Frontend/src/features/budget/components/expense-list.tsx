import { Expense } from "../../../shared/types/domain";

type ExpenseListProps = {
  expenses: Expense[];
};

export function ExpenseList({ expenses }: ExpenseListProps) {
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
