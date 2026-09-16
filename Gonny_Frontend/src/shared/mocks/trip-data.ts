import { ReportOverview } from "../types/domain";

export const mockReportOverview: ReportOverview = {
  totalSpentLabel: "480,000 KRW",
  budgetDiffLabel: "-4%",
  visitedCountLabel: "8 places",
  totalDistanceLabel: "145 km",
  insights: [
    "Food spending was 18% over budget.",
    "Travel distance was long, so a tighter route would help next time.",
    "Seongsan Ilchulbong was the most satisfying stop.",
  ],
};
