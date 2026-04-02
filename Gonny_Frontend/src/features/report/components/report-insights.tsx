type ReportInsightsProps = {
  insights: string[];
};

export function ReportInsights({ insights }: ReportInsightsProps) {
  return (
    <div className="card">
      <h2 className="section-title">AI 인사이트</h2>
      <div className="stack">
        {insights.map((insight) => (
          <div className="trip-card" key={insight}>
            {insight}
          </div>
        ))}
      </div>
    </div>
  );
}
