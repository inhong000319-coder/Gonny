type TripSummaryProps = {
  budgetLabel: string;
  weatherSummary: string;
  companionLabel: string;
};

const summaryItems = [
  { key: "budget", label: "예산" },
  { key: "weather", label: "날씨" },
  { key: "companions", label: "동행" },
] as const;

export function TripSummary({ budgetLabel, weatherSummary, companionLabel }: TripSummaryProps) {
  const values = {
    budget: budgetLabel,
    weather: weatherSummary,
    companions: companionLabel,
  };

  return (
    <div className="card">
      <div className="section-header">
        <div>
          <h2 className="section-title" style={{ fontSize: "1.55rem", marginBottom: 4 }}>
            여행 요약
          </h2>
          <p className="section-subtitle">예산·날씨·동행을 한눈에 확인해요.</p>
        </div>
      </div>
      <div className="td-summary-grid">
        {summaryItems.map((item) => (
          <div className="td-summary-item" key={item.key}>
            <strong>{item.label}</strong>
            <p>{values[item.key]}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
