type TripSummaryProps = {
  budgetLabel: string;
  weatherSummary: string;
  companionLabel: string;
};

const summaryItems = [
  { key: "budget", label: "Budget" },
  { key: "weather", label: "Weather" },
  { key: "companions", label: "Travelers" },
] as const;

export function TripSummary({ budgetLabel, weatherSummary, companionLabel }: TripSummaryProps) {
  const values = {
    budget: budgetLabel,
    weather: weatherSummary,
    companions: companionLabel,
  };

  return (
    <div className="card card-tinted">
      <div className="section-header">
        <div>
          <span className="section-kicker">Snapshot</span>
          <h2 className="section-title" style={{ fontSize: "1.55rem", marginBottom: 4 }}>
            Trip summary
          </h2>
          <p className="section-subtitle">The top-level context that should always stay easy to scan.</p>
        </div>
      </div>
      <div className="page-grid" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>
        {summaryItems.map((item) => (
          <div className="metric" key={item.key}>
            <strong>{item.label}</strong>
            <p>{values[item.key]}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
