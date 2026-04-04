type BudgetGaugeProps = {
  value: number;
};

export function BudgetGauge({ value }: BudgetGaugeProps) {
  return (
    <div className="stack">
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${value}%` }} />
      </div>
      <span className="section-subtitle" style={{ margin: 0 }}>
        사용률 {value}%
      </span>
    </div>
  );
}
