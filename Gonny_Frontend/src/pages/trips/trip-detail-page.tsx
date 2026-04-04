import { useParams } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { BudgetSummaryCard } from "../../features/budget/components/budget-summary-card";
import { ExpenseList } from "../../features/budget/components/expense-list";
import { useBudgetSummaryQuery } from "../../features/budget/hooks/use-budget-summary-query";
import { useExpensesQuery } from "../../features/budget/hooks/use-expenses-query";
import { DayTimeline } from "../../features/itinerary/components/day-timeline";
import { WeatherBanner } from "../../features/itinerary/components/weather-banner";
import { ReportInsights } from "../../features/report/components/report-insights";
import { ReportSummary } from "../../features/report/components/report-summary";
import { ShareLinkModal } from "../../features/share/components/share-link-modal";
import { TripHeader } from "../../features/trips/components/trip-header";
import { TripSummary } from "../../features/trips/components/trip-summary";
import { useTripDetailQuery } from "../../features/trips/hooks/use-trip-detail-query";
import { mockDayPlans, mockReportOverview } from "../../shared/mocks/trip-data";

export function TripDetailPage() {
  const { tripId = "101" } = useParams();
  const { data: tripDetail } = useTripDetailQuery(tripId);
  const { data: budget } = useBudgetSummaryQuery(tripId);
  const { data: expenses = [] } = useExpensesQuery(tripId);
  const primaryDayPlan = tripDetail?.dayPlans[0] ?? mockDayPlans[0];

  if (!tripDetail || !budget) {
    return (
      <AppShell>
        <div className="card">
          <h2 className="section-title">Loading trip...</h2>
          <p className="section-subtitle">Trip data is being prepared.</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <TripHeader trip={tripDetail.overview} />
      <div className="page-grid grid-two">
        <div className="stack">
          <WeatherBanner />
          <TripSummary
            budgetLabel={tripDetail.overview.budgetLabel}
            companionLabel={tripDetail.overview.companionLabel}
            weatherSummary={tripDetail.overview.weatherSummary}
          />
          <DayTimeline dayPlan={primaryDayPlan} />
        </div>
        <div className="stack">
          <BudgetSummaryCard budget={budget} />
          <ExpenseList expenses={expenses} />
          <ShareLinkModal />
        </div>
      </div>
      <div className="stack" style={{ marginTop: 20 }}>
        <ReportSummary report={mockReportOverview} />
        <ReportInsights insights={mockReportOverview.insights} />
      </div>
    </AppShell>
  );
}
