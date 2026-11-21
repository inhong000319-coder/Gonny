// Pure, React-free date/기간 계산 - 전부 "로컬(브라우저) 자정" 기준이다.
// new Date().toISOString()/new Date(dateString).toISOString()은 UTC로
// 변환하므로 KST(UTC+9)에서는 00:00~09:00 사이에 하루가 밀린다 - 이 모듈의
// 모든 함수는 그 변환을 거치지 않는다(toLocalISODate가 유일한 직렬화
// 경로이고, getFullYear/getMonth/getDate만 읽는다).

export const MAX_NIGHTS = 30;

// "YYYY-MM-DD" - Date의 로컬 연/월/일만 읽어 조립한다(toISOString 금지).
export function toLocalISODate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

// "YYYY-MM-DD" -> 그 날짜의 로컬 자정 Date. new Date("YYYY-MM-DD")는 UTC
// 자정으로 해석되므로 쓰지 않는다 - 연/월/일을 직접 생성자에 넘긴다.
export function parseLocalISODate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, (month || 1) - 1, day || 1);
}

export function addDays(date: Date, days: number): Date {
  const next = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  next.setDate(next.getDate() + days);
  return next;
}

export function addDaysToISODate(startDate: string, days: number): string {
  return toLocalISODate(addDays(parseLocalISODate(startDate), days));
}

// 두 "YYYY-MM-DD" 사이의 박수(end - start, 일 단위). end가 start보다
// 이르면 음수를 돌려준다 - 호출부가 필요에 따라 처리한다.
export function diffNights(startDate: string, endDate: string): number {
  const start = parseLocalISODate(startDate);
  const end = parseLocalISODate(endDate);
  const msPerDay = 24 * 60 * 60 * 1000;
  return Math.round((end.getTime() - start.getTime()) / msPerDay);
}

export function isSameLocalDate(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

export function startOfLocalToday(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

// 기존 동작 그대로 유지 - 서버로 보내는 duration_label 값("0박 1일" 포함)은
// 이 형식 그대로다(요청 계약 불변 - requirements #1, #7).
export function buildDurationLabel(nights: number): string {
  return `${nights}박 ${nights + 1}일`;
}

// 화면에 보여줄 때만 쓰는 표기 - 0박이면 "당일치기", 그 외엔
// buildDurationLabel과 동일. 서버로 보내는 duration_label 자체는 절대 이
// 함수를 거치지 않는다.
export function formatDurationLabel(nights: number): string {
  return nights === 0 ? "당일치기" : buildDurationLabel(nights);
}

export type ArrivalPeriodLike = "morning" | "afternoon" | "evening" | "night";
export type DeparturePeriodLike = "before_lunch" | "afternoon" | "evening_or_later";

// 당일치기(도착=출발일)에서 가능한 도착·출발 시간대 조합 - 12개 중 6개만
// 일정을 만들 수 있다(도착 후 이어지는 시간대로만 출발 가능). 백엔드
// services/arrival_departure.py의 규칙을 화면에서 미리 보여주기 위한
// 목적의 복제본 - 실제 차단은 여전히 서버가 한다(422).
const DAY_TRIP_FEASIBLE_DEPARTURES: Record<ArrivalPeriodLike, DeparturePeriodLike[]> = {
  morning: ["before_lunch", "afternoon", "evening_or_later"],
  afternoon: ["afternoon", "evening_or_later"],
  evening: ["evening_or_later"],
  night: [],
};

// arrival/departure 중 하나라도 null(상관없음)이면 제약이 없다 - true.
export function isDayTripCombinationFeasible(
  arrival: ArrivalPeriodLike | null,
  departure: DeparturePeriodLike | null,
): boolean {
  if (!arrival || !departure) {
    return true;
  }
  return DAY_TRIP_FEASIBLE_DEPARTURES[arrival].includes(departure);
}

// 당일치기일 때 주어진 도착 시간대와 "조합 가능한" 출발 시간대 목록(상관없음
// 제외) - 출발 칩을 비활성화할 때 쓴다. arrival이 null이면 전부 가능.
export function feasibleDeparturesForArrival(arrival: ArrivalPeriodLike | null): DeparturePeriodLike[] {
  if (!arrival) {
    return ["before_lunch", "afternoon", "evening_or_later"];
  }
  return DAY_TRIP_FEASIBLE_DEPARTURES[arrival];
}

export function feasibleArrivalsForDeparture(departure: DeparturePeriodLike | null): ArrivalPeriodLike[] {
  const all: ArrivalPeriodLike[] = ["morning", "afternoon", "evening", "night"];
  if (!departure) {
    return all;
  }
  return all.filter((arrival) => DAY_TRIP_FEASIBLE_DEPARTURES[arrival].includes(departure));
}
