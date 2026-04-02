import {
  BudgetOverview,
  DayPlan,
  Expense,
  ReportOverview,
  TripOverview,
  TripSummaryItem,
} from "../types/domain";

export const mockTrips: TripSummaryItem[] = [
  {
    id: "101",
    title: "제주 2박 3일",
    destination: "제주",
    startDate: "2026.05.01",
    endDate: "2026.05.03",
    status: "upcoming",
    budget: 500000,
    companionCount: 2,
  },
  {
    id: "102",
    title: "부산 미식 여행",
    destination: "부산",
    startDate: "2026.06.10",
    endDate: "2026.06.12",
    status: "completed",
    budget: 420000,
    companionCount: 1,
  },
];

export const mockTripOverview: TripOverview = {
  id: "101",
  title: "Jeju 2N3D",
  destination: "Jeju",
  dateRangeLabel: "2026.05.01 - 2026.05.03",
  weatherSummary: "Day 1 Sunny / Day 2 Rain",
  budgetLabel: "500,000 KRW",
  companionLabel: "2 travelers",
};

export const mockDayPlans: DayPlan[] = [
  {
    id: "day-1",
    dayLabel: "Day 1",
    weatherLabel: "Sunny 22C",
    totalTimeLabel: "Total est. 8h 30m",
    items: [
      {
        id: "item-1",
        time: "09:00",
        title: "Seongsan Ilchulbong",
        meta: "90 min / 40 min move / rental car",
        tip: "Arrive before 9 AM to avoid the crowd.",
      },
      {
        id: "item-2",
        time: "11:30",
        title: "Black Pork Lunch",
        meta: "60 min / 20 min move / meal",
        tip: "Check reservation status the day before to reduce waiting time.",
      },
      {
        id: "item-3",
        time: "14:00",
        title: "Cafe Delmoondo",
        meta: "60 min / 20 min move / cafe",
        tip: "Seats near sunset time fill up quickly, so arriving early helps.",
      },
    ],
  },
];

export const mockBudgetOverview: BudgetOverview = {
  totalBudget: 500000,
  totalSpent: 175000,
  remainingBudget: 325000,
  usagePercent: 35,
};

export const mockExpenses: Expense[] = [
  {
    id: "expense-1",
    category: "Food",
    amountLabel: "45,000 KRW",
    note: "Black pork lunch",
  },
  {
    id: "expense-2",
    category: "Transport",
    amountLabel: "20,000 KRW",
    note: "Fuel",
  },
];

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
