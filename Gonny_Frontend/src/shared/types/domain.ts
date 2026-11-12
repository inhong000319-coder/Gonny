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
  // "이름(유형)" 형태로 미리 포맷된 라벨 - 숙소 없이 저장된 여행(구버전
  // 포함)에서는 undefined, 그 경우 TripCard는 아무것도 그리지 않는다.
  // TripOverview.accommodationLabel과 같은 포맷터(features/trips/utils/
  // format-accommodation-label.ts)로 만들어진다.
  accommodationLabel?: string;
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
  // accommodationLabel의 원본 id - 숙소 변경 패널이 후보 목록 중 "지금
  // 저장된 숙소"를 이름 문자열이 아니라 id로 구분하기 위함.
  accommodationId?: string;
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
  // 숙박 지출은 제외한 금액 - remainingBudget/usagePercent도 이 값 기준이다.
  totalSpent: number;
  remainingBudget: number;
  usagePercent: number;
  // 숙박 지출 합계(참고용) - totalSpent/remainingBudget/usagePercent에는 포함되지 않는다.
  lodgingSpent?: number;
};

export type Expense = {
  id: string;
  category: string;
  amountLabel: string;
  note: string;
};
