export type TripStatus = "upcoming" | "ongoing" | "completed";

export type User = {
  id: number;
  nickname: string;
  email: string;
};

// #135 - 분할 저장된 여행의 숙소 구역 하나(camelCase로 옮긴 TripStayDto).
export type TripStayOverview = {
  stayIndex: number;
  startNight: number;
  nights: number;
  accommodationId: string;
  accommodationName: string;
  accommodationType: string;
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
  // 한 곳이면 "이름(유형)", 2곳 이상이면 "이름(유형) 외 N곳" - 숙소 없이
  // 저장된 여행(구버전 포함)에서는 undefined, 그 경우 TripCard는 아무것도
  // 그리지 않는다. features/trips/utils/format-accommodation-label.ts의
  // formatTripCardAccommodationLabel로 만들어진다.
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
  // 한 곳이면 "이름(유형)", 2곳 이상이면 숙소 이름을 " → "로 이어붙인
  // 문자열 - 숙소 없이 저장된 여행(구버전 포함)에서는 undefined, 그 경우
  // 호출부는 아무것도 그리지 않는다. formatTripHeaderAccommodationLabel로
  // 만들어진다.
  accommodationLabel?: string;
  // #135 - 항상 존재(숙소 없으면 []). 길이 1이면 기존과 같은 단일 숙소
  // 여행, 2곳 이상이면 분할 저장된 여행 - AccommodationChangePanel이
  // stay별로 바꾸기 위해 이 원본 목록을 그대로 쓴다.
  stays: TripStayOverview[];
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
