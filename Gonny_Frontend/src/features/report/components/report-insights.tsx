type ReportInsightsProps = {
  insights: string[];
};

// "AI 인사이트"라고 부르지 않는다 - 실시간 LLM 호출 없이 실제 계산값을
// 규칙 기반 문장으로 만든 것이라, "AI가 생성했다"는 표현은 정확하지 않다.
export function ReportInsights({ insights }: ReportInsightsProps) {
  return (
    <div className="card">
      <h2 className="section-title">여행 인사이트</h2>
      <div className="stack">
        {insights.length > 0 ? (
          insights.map((insight) => (
            <div className="trip-card" key={insight}>
              {insight}
            </div>
          ))
        ) : (
          <p className="section-subtitle" style={{ marginBottom: 0 }}>
            아직 보여드릴 인사이트가 없어요.
          </p>
        )}
      </div>
    </div>
  );
}
