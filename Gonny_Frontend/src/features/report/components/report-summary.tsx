type ReportSummaryProps = {
  totalSpent: number;
  budget: number;
  budgetDiffPct: number | null;
  visitedCount: number;
  distanceKm: number | null;
};

function formatWon(value: number) {
  return `${value.toLocaleString("ko-KR")}원`;
}

function formatBudgetDiff(pct: number | null) {
  if (pct === null) {
    return "정보 없음";
  }
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct}%`;
}

function formatDistance(km: number | null) {
  if (km === null) {
    return "정보 없음";
  }
  return `${km}km`;
}

export function ReportSummary({ totalSpent, budget, budgetDiffPct, visitedCount, distanceKm }: ReportSummaryProps) {
  return (
    <div className="card">
      <h2 className="section-title">여행 회고</h2>
      <div className="page-grid" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
        <div className="metric">
          <strong>총 지출</strong>
          <p>{formatWon(totalSpent)}</p>
          <span>예산 {formatWon(budget)} 기준</span>
        </div>
        <div className="metric">
          <strong>예산 대비</strong>
          <p>{formatBudgetDiff(budgetDiffPct)}</p>
        </div>
        <div className="metric">
          <strong>방문 장소</strong>
          <p>{visitedCount}곳</p>
        </div>
        <div className="metric">
          <strong>총 이동 거리</strong>
          <p>{formatDistance(distanceKm)}</p>
        </div>
      </div>
    </div>
  );
}
