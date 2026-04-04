import { ReportOverview } from "../../../shared/types/domain";

type ReportSummaryProps = {
  report: ReportOverview;
};

export function ReportSummary({ report }: ReportSummaryProps) {
  return (
    <div className="card">
      <h2 className="section-title">여행 회고</h2>
      <div className="page-grid" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
        <div className="metric">
          <strong>총 지출</strong>
          <p>{report.totalSpentLabel}</p>
        </div>
        <div className="metric">
          <strong>예산 대비</strong>
          <p>{report.budgetDiffLabel}</p>
        </div>
        <div className="metric">
          <strong>방문 완료</strong>
          <p>{report.visitedCountLabel}</p>
        </div>
        <div className="metric">
          <strong>총 이동 거리</strong>
          <p>{report.totalDistanceLabel}</p>
        </div>
      </div>
    </div>
  );
}
