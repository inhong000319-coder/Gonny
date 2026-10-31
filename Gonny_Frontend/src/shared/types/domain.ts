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
  isFavorite: boolean;
};

export type TripOverview = {
  id: string;
  title: string;
  destination: string;
  dateRangeLabel: string;
  weatherSummary: string;
  budgetLabel: string;
  companionLabel: string;
  // "이름(유형)" 형태로 미리 포맷된 라벨 - 숙소 없이 저장된 여행(구버전
  // 포함)에서는 undefined, 그 경우 호출부는 아무것도 그리지 않는다.
  accommodationLabel?: string;
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
