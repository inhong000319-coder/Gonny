export type TripStatus = "upcoming" | "ongoing" | "completed";

export type User = {
  id: number;
  nickname: string;
  email: string;
};

export type TripSummaryItem = {
  id: string;
  title: string;
  destination: string;
  startDate: string;
  endDate: string;
  status: TripStatus;
  budget: number;
  companionCount: number;
};

export type TripOverview = {
  id: string;
  title: string;
  destination: string;
  dateRangeLabel: string;
  weatherSummary: string;
  budgetLabel: string;
  companionLabel: string;
};

export type ItineraryItem = {
  id: string;
  time: string;
  title: string;
  meta: string;
  tip: string;
};

export type DayPlan = {
  id: string;
  dayLabel: string;
  weatherLabel: string;
  totalTimeLabel: string;
  items: ItineraryItem[];
};

export type BudgetOverview = {
  totalBudget: number;
  totalSpent: number;
  remainingBudget: number;
  usagePercent: number;
};

export type Expense = {
  id: string;
  category: string;
  amountLabel: string;
  note: string;
};

export type ReportOverview = {
  totalSpentLabel: string;
  budgetDiffLabel: string;
  visitedCountLabel: string;
  totalDistanceLabel: string;
  insights: string[];
};
