import { Fragment, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../../../shared/api/client";
import { PRICE_REFERENCE_PERIOD, formatApproxManwon, formatApproxManwonRange } from "../../../shared/pricing";
import { createItineraryItem } from "../../itinerary/api/create-itinerary-item";
import { WeatherBanner } from "../../itinerary/components/weather-banner";
import { createTrip } from "../../trips/api/create-trip";
import {
  createItineraryDocDownload,
  createItineraryPrintPreview,
  revokeItineraryExportUrl,
} from "../../../shared/itinerary-export";

type CatalogCityOption = {
  continent: string;
  country: string;
  city: string;
  aliases: string[];
  accommodation_type_counts?: Partial<Record<AccommodationTypeLabel, number>>;
};

type RuleItineraryCatalogResponse = {
  cities?: CatalogCityOption[];
};

type TimeSlot = "morning" | "afternoon" | "evening";
type BudgetBand = "low" | "medium" | "high";
type TripStyle = "tight" | "easy" | "near-stay" | "mobility-first";
type CompanionType = "solo" | "couple" | "friend" | "family";
type TripConcept =
  | "food"
  | "shopping"
  | "relax"
  | "sightseeing"
  | "culture"
  | "nature"
  | "activity"
  | "nightlife"
  | "onsen";

type RuleItineraryItem = {
  day_number: number;
  time_slot: TimeSlot;
  place_name: string;
  category: string;
  area: string;
  notes: string;
  // Straight-line travel-time estimate from the previous slot's place, in
  // minutes - null for a day's first slot or a full-day place (see the
  // backend's RuleItineraryItem docstring).
  travel_minutes_from_previous: number | null;
  // Representative adult admission in KRW (0 = confirmed free, null = unknown).
  average_cost_krw?: number | null;
};

type RuleDayDurationWarning = {
  day_number: number;
  estimated_total_minutes: number;
  message: string;
};

type RuleClosedDayExclusion = {
  day_number: number;
  place_name: string;
  message: string;
};

type RuleWeatherAlert = {
  day_number: number;
  condition: "rain" | "snow";
  precipitation_mm: number;
  affected_place_names: string[];
  suggested_alternatives: string[];
};

// Field shape deliberately mirrors RuleItineraryItem (minus category,
// which every meal implicitly is "food") - see the backend's
// RuleMealRecommendation schema. Recommended independently per day,
// outside the morning/afternoon/evening slot competition - same spirit
// as accommodation_recommendation being separate from items, just
// repeated per day instead of once for the whole trip.
type RuleMealRecommendation = {
  day_number: number;
  meal_type: "lunch" | "dinner";
  place_name: string;
  area: string;
  notes: string;
  travel_minutes_from_previous: number | null;
};

// view(숙소 조망)는 데이터 신뢰도 문제로 이번 범위에서 표시하지 않는다.
type AccommodationRecommendation = {
  id: string;
  name: string;
  accommodation_type: string;
  checkin_time?: string | null;
  checkout_time?: string | null;
  // Standard room, one night, in KRW (null = no confirmed figure).
  average_price_krw?: number | null;
};

type RuleCostEstimate = {
  min_krw: number;
  max_krw: number;
  priced_place_count: number;
  unpriced_place_count: number;
  accommodation_included: boolean;
  nights: number;
  travelers: number;
};

// The trip-level mode the user actually picks per day (no "walk" - that's
// a per-leg day_travel option, not a day plan). Matches the backend's
// RuleItineraryRequest.transport_by_day.
type DayTransportMode = "transit" | "car";
type TransportMode = "walk" | "transit" | "car";
type TravelEstimateSource = "estimate" | "api";
type TravelLegPointKind = "accommodation" | "place" | "meal";

type RuleTravelOption = {
  mode: TransportMode;
  minutes: number;
};

type RuleTravelLeg = {
  day_number: number;
  from_name: string;
  to_name: string;
  from_kind: TravelLegPointKind;
  to_kind: TravelLegPointKind;
  distance_km: number;
  options: RuleTravelOption[];
  source: TravelEstimateSource;
};

// A day only appears here when expected_leg_count > 0 (the backend's
// itinerary genuinely has something to estimate for that day) - legs can
// still be a partial (or empty) subset of expected_leg_count when some
// place/accommodation lacks coordinates, see missing_leg_count.
type RuleDayTravel = {
  day_number: number;
  legs: RuleTravelLeg[];
  transit_total_minutes: number;
  car_total_minutes: number;
  expected_leg_count: number;
  missing_leg_count: number;
};

type FeaturedVideo = {
  video_id: string;
  title: string;
  channel: string;
  view_count_text: string;
  published?: string | null;
  youtube_url?: string | null;
  embed_url?: string | null;
  thumbnail_url?: string | null;
};

type RuleItineraryResponse = {
  continent: string;
  country: string;
  city: string;
  travelers: number;
  nights: number;
  days: number;
  budget_band: BudgetBand;
  concepts: TripConcept[];
  style: TripStyle;
  companion_type: CompanionType;
  featured_video?: FeaturedVideo | null;
  items: RuleItineraryItem[];
  day_duration_warnings: RuleDayDurationWarning[];
  closed_day_exclusions: RuleClosedDayExclusion[];
  weather_alerts: RuleWeatherAlert[];
  accommodation_recommendation: AccommodationRecommendation | null;
  meal_recommendations: RuleMealRecommendation[];
  estimated_cost: RuleCostEstimate | null;
  day_travel: RuleDayTravel[];
  transport_by_day: DayTransportMode[] | null;
};

type PlannerFormState = {
  city: string;
  travelers: number;
  start_date: string;
  duration_label: string;
  budget_band: BudgetBand;
  concepts: TripConcept[];
  style: TripStyle;
  companion_type: CompanionType;
  accommodation_types: AccommodationTypeLabel[];
  accommodation_budget_band: BudgetBand | null;
  // Modes the user has toggled on (at least one, always). transport_by_day
  // is the day-by-day assignment actually sent to the backend - its length
  // always equals the trip's day count (nights + 1).
  transport_modes: DayTransportMode[];
  transport_by_day: DayTransportMode[];
};

const STEP_COUNT = 4;
const conceptOptions: TripConcept[] = [
  "food",
  "shopping",
  "relax",
  "sightseeing",
  "culture",
  "nature",
  "activity",
  "nightlife",
  "onsen",
];
const budgetOptions: BudgetBand[] = ["low", "medium", "high"];
type AccommodationTypeLabel = "호텔" | "모텔" | "호스텔" | "펜션·민박" | "콘도미니엄";
const accommodationTypeOptions: AccommodationTypeLabel[] = ["호텔", "모텔", "호스텔", "펜션·민박", "콘도미니엄"];
const styleOptions: TripStyle[] = ["tight", "easy", "near-stay", "mobility-first"];
const companionOptions: CompanionType[] = ["solo", "couple", "friend", "family"];
const travelerOptions = [
  { value: 1, label: "혼자 여행" },
  { value: 2, label: "둘이서 여행" },
  { value: 3, label: "셋이서 여행" },
  { value: 4, label: "넷이서 여행" },
  { value: 5, label: "5인 이상 여행" },
];
const nightsOptions = [1, 2, 3, 4, 5, 6];
// Trip.budget is a required integer on save, but the planner no longer
// collects a won amount. 0 is what the backend's report/expense code
// already treats as "no budget set" (see TripService.get_trip_report).
const UNSET_TRIP_BUDGET = 0;

const initialForm: PlannerFormState = {
  city: "",
  travelers: 2,
  start_date: new Date().toISOString().slice(0, 10),
  duration_label: "2박 3일",
  budget_band: "medium",
  concepts: ["sightseeing", "food"],
  style: "easy",
  companion_type: "friend",
  accommodation_types: [],
  accommodation_budget_band: null,
  transport_modes: ["transit"],
  transport_by_day: ["transit", "transit", "transit"],
};

const cityKo: Record<string, string> = {
  bangkok: "방콕",
  barcelona: "바르셀로나",
  busan: "부산",
  chiangmai: "치앙마이",
  fukuoka: "후쿠오카",
  gangneung: "강릉",
  gyeongju: "경주",
  jeju: "제주",
  jeonju: "전주",
  kyoto: "교토",
  osaka: "오사카",
  paris: "파리",
  rome: "로마",
  seoul: "서울",
  singapore: "싱가포르",
  sokcho: "속초",
  taipei: "타이베이",
  tokyo: "도쿄",
  vladivostok: "블라디보스토크",
  yeosu: "여수",
};

function toCityLabel(value: string) {
  return cityKo[value] ?? value;
}

function labelConcept(value: TripConcept) {
  if (value === "food") return "미식";
  if (value === "shopping") return "쇼핑";
  if (value === "relax") return "휴양";
  if (value === "sightseeing") return "관광";
  if (value === "culture") return "문화";
  return "자연";
}

function labelTripConcept(value: TripConcept) {
  if (value === "food") return "미식";
  if (value === "shopping") return "쇼핑";
  if (value === "relax") return "휴양";
  if (value === "sightseeing") return "관광";
  if (value === "culture") return "문화";
  if (value === "activity") return "액티비티";
  if (value === "nightlife") return "나이트라이프";
  if (value === "onsen") return "온천";
  return "자연";
}

function labelBudget(value: BudgetBand) {
  if (value === "low") return "가볍게";
  if (value === "medium") return "균형 있게";
  return "조금 더 여유 있게";
}

function budgetIntensityLabel(value: BudgetBand) {
  if (value === "low") return "숙소와 식사를 합리적으로 고르는 절약형";
  if (value === "medium") return "가격과 만족도의 균형을 맞춘 기본형";
  return "숙소와 경험에 여유를 더한 프리미엄형";
}

function budgetHint(value: BudgetBand) {
  if (value === "low") return "가성비 좋은 동선으로 추천합니다.";
  if (value === "medium") return "비용과 만족도를 함께 챙깁니다.";
  return "조금 더 편안한 경험을 우선합니다.";
}

function labelStyle(value: TripStyle) {
  if (value === "tight") return "꽉 차게";
  if (value === "easy") return "여유 있게";
  if (value === "near-stay") return "숙소 근처 중심";
  return "이동 편의 우선";
}

function labelStyleDesc(value: TripStyle) {
  if (value === "tight") return "핵심 장소를 빠르게 많이 둘러봐요.";
  if (value === "easy") return "이동 부담을 줄이고 흐름을 부드럽게 잡아요.";
  if (value === "near-stay") return "한 지역에 머물며 편하게 즐겨요.";
  return "동선 효율과 접근성을 우선해요.";
}

function labelCompanion(value: CompanionType) {
  if (value === "solo") return "혼자";
  if (value === "couple") return "커플";
  if (value === "friend") return "친구";
  return "가족";
}

function labelCompanionDesc(value: CompanionType) {
  if (value === "solo") return "혼자 움직이기 부담 없는 일정";
  if (value === "couple") return "분위기와 여유를 살린 일정";
  if (value === "friend") return "함께 즐기기 좋은 활기 있는 일정";
  return "무리 없이 둘러보기 좋은 일정";
}

function labelTimeSlot(value: TimeSlot) {
  if (value === "morning") return "오전";
  if (value === "afternoon") return "오후";
  return "저녁";
}

function buildDurationLabel(nights: number) {
  return `${nights}박 ${nights + 1}일`;
}

function buildEndDate(startDate: string, nights: number) {
  const parsed = new Date(startDate);
  if (Number.isNaN(parsed.getTime())) {
    return startDate;
  }
  parsed.setDate(parsed.getDate() + nights);
  return parsed.toISOString().slice(0, 10);
}

function parseNights(value: string) {
  const match = value.match(/(\d+)\s*박/);
  if (!match) {
    return 2;
  }

  return Number(match[1]);
}

function isCatalogCityOption(value: unknown): value is CatalogCityOption {
  if (!value || typeof value !== "object") {
    return false;
  }

  const option = value as Record<string, unknown>;
  return (
    typeof option.continent === "string" &&
    typeof option.country === "string" &&
    typeof option.city === "string" &&
    Array.isArray(option.aliases)
  );
}

function isRuleItineraryItem(value: unknown): value is RuleItineraryItem {
  if (!value || typeof value !== "object") {
    return false;
  }

  const item = value as Record<string, unknown>;
  return (
    typeof item.day_number === "number" &&
    typeof item.time_slot === "string" &&
    typeof item.place_name === "string" &&
    typeof item.category === "string" &&
    typeof item.area === "string" &&
    typeof item.notes === "string" &&
    (item.travel_minutes_from_previous === null || typeof item.travel_minutes_from_previous === "number")
  );
}

function isRuleDayDurationWarning(value: unknown): value is RuleDayDurationWarning {
  if (!value || typeof value !== "object") {
    return false;
  }

  const warning = value as Record<string, unknown>;
  return (
    typeof warning.day_number === "number" &&
    typeof warning.estimated_total_minutes === "number" &&
    typeof warning.message === "string"
  );
}

function isRuleClosedDayExclusion(value: unknown): value is RuleClosedDayExclusion {
  if (!value || typeof value !== "object") {
    return false;
  }

  const exclusion = value as Record<string, unknown>;
  return (
    typeof exclusion.day_number === "number" &&
    typeof exclusion.place_name === "string" &&
    typeof exclusion.message === "string"
  );
}

function isRuleWeatherAlert(value: unknown): value is RuleWeatherAlert {
  if (!value || typeof value !== "object") {
    return false;
  }

  const alert = value as Record<string, unknown>;
  return (
    typeof alert.day_number === "number" &&
    (alert.condition === "rain" || alert.condition === "snow") &&
    typeof alert.precipitation_mm === "number" &&
    Array.isArray(alert.affected_place_names) &&
    alert.affected_place_names.every((name) => typeof name === "string") &&
    Array.isArray(alert.suggested_alternatives) &&
    alert.suggested_alternatives.every((name) => typeof name === "string")
  );
}

function isRuleMealRecommendation(value: unknown): value is RuleMealRecommendation {
  if (!value || typeof value !== "object") {
    return false;
  }

  const meal = value as Record<string, unknown>;
  return (
    typeof meal.day_number === "number" &&
    (meal.meal_type === "lunch" || meal.meal_type === "dinner") &&
    typeof meal.place_name === "string" &&
    typeof meal.area === "string" &&
    typeof meal.notes === "string" &&
    (meal.travel_minutes_from_previous === null || typeof meal.travel_minutes_from_previous === "number")
  );
}

function isAccommodationRecommendation(value: unknown): value is AccommodationRecommendation {
  if (!value || typeof value !== "object") {
    return false;
  }

  const accommodation = value as Record<string, unknown>;
  return (
    typeof accommodation.id === "string" &&
    typeof accommodation.name === "string" &&
    typeof accommodation.accommodation_type === "string"
  );
}

function isRuleCostEstimate(value: unknown): value is RuleCostEstimate {
  if (!value || typeof value !== "object") {
    return false;
  }

  const estimate = value as Record<string, unknown>;
  return (
    typeof estimate.min_krw === "number" &&
    typeof estimate.max_krw === "number" &&
    typeof estimate.priced_place_count === "number" &&
    typeof estimate.unpriced_place_count === "number" &&
    typeof estimate.accommodation_included === "boolean"
  );
}

function isRuleTravelOption(value: unknown): value is RuleTravelOption {
  if (!value || typeof value !== "object") {
    return false;
  }

  const option = value as Record<string, unknown>;
  return (
    (option.mode === "walk" || option.mode === "transit" || option.mode === "car") &&
    typeof option.minutes === "number"
  );
}

function isTravelLegPointKind(value: unknown): value is TravelLegPointKind {
  return value === "accommodation" || value === "place" || value === "meal";
}

function isRuleTravelLeg(value: unknown): value is RuleTravelLeg {
  if (!value || typeof value !== "object") {
    return false;
  }

  const leg = value as Record<string, unknown>;
  return (
    typeof leg.day_number === "number" &&
    typeof leg.from_name === "string" &&
    typeof leg.to_name === "string" &&
    isTravelLegPointKind(leg.from_kind) &&
    isTravelLegPointKind(leg.to_kind) &&
    typeof leg.distance_km === "number" &&
    Array.isArray(leg.options) &&
    leg.options.every(isRuleTravelOption) &&
    (leg.source === "estimate" || leg.source === "api")
  );
}

function isRuleDayTravel(value: unknown): value is RuleDayTravel {
  if (!value || typeof value !== "object") {
    return false;
  }

  const day = value as Record<string, unknown>;
  return (
    typeof day.day_number === "number" &&
    Array.isArray(day.legs) &&
    day.legs.every(isRuleTravelLeg) &&
    typeof day.transit_total_minutes === "number" &&
    typeof day.car_total_minutes === "number" &&
    typeof day.expected_leg_count === "number" &&
    typeof day.missing_leg_count === "number"
  );
}

function isDayTransportModeArray(value: unknown): value is DayTransportMode[] {
  return Array.isArray(value) && value.every((item) => item === "transit" || item === "car");
}

function formatCostLabel(value: number) {
  return value === 0 ? "무료" : `${value.toLocaleString("ko-KR")}원`;
}

function normalizeCatalogResponse(payload: unknown) {
  if (!payload || typeof payload !== "object") {
    return [];
  }

  const data = payload as RuleItineraryCatalogResponse;
  if (!Array.isArray(data.cities)) {
    return [];
  }

  return data.cities.filter(isCatalogCityOption);
}

function normalizeGenerateResponse(payload: unknown): RuleItineraryResponse {
  if (!payload || typeof payload !== "object") {
    throw new Error("일정 생성 응답 형식이 올바르지 않습니다.");
  }

  const data = payload as Partial<RuleItineraryResponse>;
  if (!Array.isArray(data.items)) {
    throw new Error("생성된 일정 항목이 없습니다.");
  }

  const items = data.items.filter(isRuleItineraryItem);
  if (items.length === 0) {
    throw new Error("생성된 일정 항목을 해석하지 못했습니다.");
  }

  return {
    continent: typeof data.continent === "string" ? data.continent : "",
    country: typeof data.country === "string" ? data.country : "",
    city: typeof data.city === "string" ? data.city : "",
    travelers: typeof data.travelers === "number" ? data.travelers : 0,
    nights: typeof data.nights === "number" ? data.nights : 0,
    days: typeof data.days === "number" ? data.days : 0,
    budget_band: (data.budget_band as BudgetBand) ?? "medium",
    concepts: Array.isArray(data.concepts) ? (data.concepts as TripConcept[]) : [],
    style: (data.style as TripStyle) ?? "easy",
    companion_type: (data.companion_type as CompanionType) ?? "friend",
    featured_video:
      data.featured_video && typeof data.featured_video === "object" ? (data.featured_video as FeaturedVideo) : null,
    items,
    day_duration_warnings: Array.isArray(data.day_duration_warnings)
      ? data.day_duration_warnings.filter(isRuleDayDurationWarning)
      : [],
    closed_day_exclusions: Array.isArray(data.closed_day_exclusions)
      ? data.closed_day_exclusions.filter(isRuleClosedDayExclusion)
      : [],
    weather_alerts: Array.isArray(data.weather_alerts) ? data.weather_alerts.filter(isRuleWeatherAlert) : [],
    accommodation_recommendation: isAccommodationRecommendation(data.accommodation_recommendation)
      ? data.accommodation_recommendation
      : null,
    meal_recommendations: Array.isArray(data.meal_recommendations)
      ? data.meal_recommendations.filter(isRuleMealRecommendation)
      : [],
    estimated_cost: isRuleCostEstimate(data.estimated_cost) ? data.estimated_cost : null,
    day_travel: Array.isArray(data.day_travel) ? data.day_travel.filter(isRuleDayTravel) : [],
    transport_by_day: isDayTransportModeArray(data.transport_by_day) ? data.transport_by_day : null,
  };
}

function groupByDay(items: RuleItineraryItem[]) {
  return items.reduce<Array<{ day: number; items: RuleItineraryItem[] }>>((groups, item) => {
    const current = groups.find((group) => group.day === item.day_number);
    if (current) {
      current.items.push(item);
      return groups;
    }

    groups.push({ day: item.day_number, items: [item] });
    return groups;
  }, []);
}

function groupMealsByDay(meals: RuleMealRecommendation[]) {
  const byDay = new Map<number, { lunch?: RuleMealRecommendation; dinner?: RuleMealRecommendation }>();
  for (const meal of meals) {
    const entry = byDay.get(meal.day_number) ?? {};
    if (meal.meal_type === "lunch") {
      entry.lunch = meal;
    } else {
      entry.dinner = meal;
    }
    byDay.set(meal.day_number, entry);
  }
  return byDay;
}

// --- Mode-aware day travel (day_travel) ------------------------------------

function defaultDayTravelMode(city: string): "transit" | "car" {
  return city === "jeju" ? "car" : "transit";
}

// --- Transport mode selection (trip-create form) ---------------------------

function labelTransportModeChoice(mode: DayTransportMode) {
  return mode === "transit" ? "대중교통" : "렌터카·자차";
}

function summarizeTransportByDay(transportByDay: DayTransportMode[]) {
  if (transportByDay.length === 0) {
    return "";
  }
  const allSame = transportByDay.every((mode) => mode === transportByDay[0]);
  if (allSame) {
    return labelTransportModeChoice(transportByDay[0]);
  }
  return transportByDay.map((mode, index) => `${index + 1}일차 ${labelTransportModeChoice(mode)}`).join(" · ");
}

// Resizes transport_by_day to match a new day count, truncating or padding
// with the last entry, and swaps any entry that's no longer in
// allowedModes (e.g. the day count shrank/changed independent of mode
// selection) for allowedModes[0].
function resizeTransportByDay(
  current: DayTransportMode[],
  days: number,
  allowedModes: DayTransportMode[],
): DayTransportMode[] {
  const fallback = allowedModes[0] ?? "transit";
  const sanitized = current.map((mode) => (allowedModes.includes(mode) ? mode : fallback));
  if (sanitized.length === days) {
    return sanitized;
  }
  if (sanitized.length > days) {
    return sanitized.slice(0, days);
  }
  const lastMode = sanitized[sanitized.length - 1] ?? fallback;
  return [...sanitized, ...Array.from({ length: days - sanitized.length }, () => lastMode)];
}

function labelTransportMode(mode: "transit" | "car") {
  return mode === "transit" ? "대중교통" : "자동차";
}

function formatTravelMinutesLabel(totalMinutes: number) {
  if (totalMinutes < 60) {
    return `${totalMinutes}분`;
  }
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return minutes > 0 ? `${hours}시간 ${minutes}분` : `${hours}시간`;
}

// Legs are matched by (kind, name) on both ends, never by position - a day
// with a dropped (coordinate-missing) leg would otherwise shift every
// later leg out of alignment with the cards it's meant to sit between.
function travelLegKey(fromKind: TravelLegPointKind, fromName: string, toKind: TravelLegPointKind, toName: string) {
  return `${fromKind}::${fromName}::${toKind}::${toName}`;
}

type DayTimelineEntry =
  | { type: "item"; item: RuleItineraryItem }
  | { type: "meal"; meal: RuleMealRecommendation };

function buildDayTimelineEntries(
  items: RuleItineraryItem[],
  dayMeals: { lunch?: RuleMealRecommendation; dinner?: RuleMealRecommendation } | undefined,
): DayTimelineEntry[] {
  const entries: DayTimelineEntry[] = [];
  for (const item of items) {
    entries.push({ type: "item", item });
    if (item.time_slot === "morning" && dayMeals?.lunch) {
      entries.push({ type: "meal", meal: dayMeals.lunch });
    }
    if (item.time_slot === "afternoon" && dayMeals?.dinner) {
      entries.push({ type: "meal", meal: dayMeals.dinner });
    }
  }
  return entries;
}

function dayTimelineEntryKind(entry: DayTimelineEntry): "place" | "meal" {
  return entry.type === "item" ? "place" : "meal";
}

function dayTimelineEntryName(entry: DayTimelineEntry): string {
  return entry.type === "item" ? entry.item.place_name : entry.meal.place_name;
}

function DayTravelPanel({
  dayTravel,
  mode,
  onModeChange,
}: {
  dayTravel: RuleDayTravel;
  mode: "transit" | "car";
  onModeChange: (mode: "transit" | "car") => void;
}) {
  const otherMode: "transit" | "car" = mode === "transit" ? "car" : "transit";
  const selectedTotal = mode === "transit" ? dayTravel.transit_total_minutes : dayTravel.car_total_minutes;
  const otherTotal = mode === "transit" ? dayTravel.car_total_minutes : dayTravel.transit_total_minutes;
  const hasLegs = dayTravel.legs.length > 0;

  return (
    <div className="tc-day-mode">
      <div aria-label="이동수단 선택" className="tc-segment" role="group">
        {(["transit", "car"] as const).map((option) => (
          <button
            aria-pressed={mode === option}
            className={mode === option ? "tc-segment-btn is-selected" : "tc-segment-btn"}
            key={option}
            onClick={() => onModeChange(option)}
            type="button"
          >
            {labelTransportMode(option)}
          </button>
        ))}
      </div>
      {hasLegs ? (
        <p className="tc-day-mode-summary">
          <strong>
            이동 합계 {dayTravel.missing_leg_count > 0 ? "최소 " : ""}약 {formatTravelMinutesLabel(selectedTotal)}
          </strong>
          <span>
            {labelTransportMode(otherMode)} 약 {formatTravelMinutesLabel(otherTotal)}
          </span>
        </p>
      ) : (
        <div className="tc-alert tc-alert-info">이동시간 정보가 부족해요</div>
      )}
      {hasLegs && dayTravel.missing_leg_count > 0 ? (
        <div className="tc-alert tc-alert-warning">
          일부 구간 정보 없음 ({dayTravel.missing_leg_count}개 구간 제외)
        </div>
      ) : null}
    </div>
  );
}

function TravelConnectorRow({
  leg,
  mode,
  label,
}: {
  leg: RuleTravelLeg;
  mode: "transit" | "car";
  label?: string;
}) {
  const modeOption = leg.options.find((option) => option.mode === mode);
  const walkOption = leg.options.find((option) => option.mode === "walk");
  const otherMode: "transit" | "car" = mode === "transit" ? "car" : "transit";
  const otherOption = leg.options.find((option) => option.mode === otherMode);
  const useWalk = walkOption != null && modeOption != null && walkOption.minutes <= modeOption.minutes;
  const primaryText = useWalk
    ? `도보 약 ${walkOption.minutes}분`
    : modeOption
      ? `${labelTransportMode(mode)} 약 ${modeOption.minutes}분`
      : null;

  return (
    <div className="tc-connector">
      {label ? <span className="tc-connector-label">{label}</span> : null}
      {primaryText ? <span className="tc-connector-primary">{primaryText}</span> : null}
      {otherOption ? (
        <span>
          {labelTransportMode(otherMode)} 약 {otherOption.minutes}분
        </span>
      ) : null}
    </div>
  );
}

function MealCard({ meal, showTravelTime = true }: { meal: RuleMealRecommendation; showTravelTime?: boolean }) {
  const note = splitNoteLines(meal.notes);

  return (
    <div className="tc-stop is-meal">
      <div className="tc-stop-time">
        <span>{meal.meal_type === "lunch" ? "점심" : "저녁"}</span>
      </div>
      <div className="tc-stop-body">
        {showTravelTime && meal.travel_minutes_from_previous !== null ? (
          <p className="tc-stop-fallback-travel">이전 장소에서 약 {meal.travel_minutes_from_previous}분 이동</p>
        ) : null}
        <div className="tc-stop-name-row">
          <strong className="tc-stop-name">{meal.place_name}</strong>
          <span className="tc-stop-chip">식사</span>
        </div>
        <p className="tc-stop-area">{meal.area}</p>
        {note.headline ? <p className="tc-stop-note-lead">{note.headline}</p> : null}
        {note.details.map((line, index) => (
          <p key={`${meal.place_name}-note-${index}`} className="tc-stop-note-line">
            {line}
          </p>
        ))}
      </div>
    </div>
  );
}

function countDistinctAreas(items: RuleItineraryItem[]) {
  return new Set(items.map((item) => item.area)).size;
}

function summarizeRoute(items: RuleItineraryItem[]) {
  if (items.length === 0) {
    return "";
  }

  const highlights = items.slice(0, 3).map((item) => item.place_name);
  return highlights.join(" · ");
}

function splitNoteLines(note: string) {
  const lines = note
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  return {
    headline: lines[0] ?? "",
    details: lines.slice(1),
  };
}

export function TripCreateForm() {
  const navigate = useNavigate();
  const [form, setForm] = useState<PlannerFormState>(initialForm);
  const [isAccommodationBudgetOn, setIsAccommodationBudgetOn] = useState(false);
  const [catalog, setCatalog] = useState<CatalogCityOption[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [currentStep, setCurrentStep] = useState(1);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSavingTrip, setIsSavingTrip] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<RuleItineraryResponse | null>(null);
  const [dayTravelMode, setDayTravelMode] = useState<Record<number, "transit" | "car">>({});
  const [docDownload, setDocDownload] = useState<{ href: string; filename: string } | null>(null);
  const [printPreview, setPrintPreview] = useState<{ href: string; filename: string } | null>(null);
  const hasResult = result !== null;

  useEffect(() => {
    if (!result) {
      setDayTravelMode({});
      return;
    }

    const defaults: Record<number, "transit" | "car"> = {};
    for (const dayTravel of result.day_travel) {
      defaults[dayTravel.day_number] = result.transport_by_day?.[dayTravel.day_number - 1] ?? defaultDayTravelMode(result.city);
    }
    setDayTravelMode(defaults);
  }, [result]);

  useEffect(() => {
    async function loadCatalog() {
      setCatalogLoading(true);
      setError("");

      try {
        const response = await apiClient.get<unknown>("/rule-itinerary/options");
        const nextCatalog = normalizeCatalogResponse(response.data);
        setCatalog(nextCatalog);

        if (nextCatalog.length === 0) {
          setError("도시 목록을 아직 불러오지 못했습니다. 잠시 뒤 다시 시도해 주세요.");
        }
      } catch (loadError) {
        const nextError = loadError instanceof Error ? loadError.message : "도시 목록을 불러오지 못했습니다.";
        setCatalog([]);
        setError(nextError);
      } finally {
        setCatalogLoading(false);
      }
    }

    void loadCatalog();
  }, []);

  const cities = useMemo(
    () => [...catalog].sort((left, right) => toCityLabel(left.city).localeCompare(toCityLabel(right.city), "ko")),
    [catalog],
  );

  const groupedItems = useMemo(() => groupByDay(result?.items ?? []), [result]);
  const mealsByDay = useMemo(() => groupMealsByDay(result?.meal_recommendations ?? []), [result]);
  const dayTravelByDay = useMemo(
    () => new Map((result?.day_travel ?? []).map((dayTravel) => [dayTravel.day_number, dayTravel])),
    [result],
  );
  const allTravelLegs = useMemo(
    () => (result?.day_travel ?? []).flatMap((dayTravel) => dayTravel.legs),
    [result],
  );
  const showTravelEstimateNotice =
    allTravelLegs.length > 0 && allTravelLegs.every((leg) => leg.source === "estimate");
  const selectedNights = parseNights(form.duration_label);
  const totalAreaCount = result ? countDistinctAreas(result.items) : 0;
  const selectedCatalogCity = cities.find((option) => option.city === form.city);
  const availableAccommodationTypes = accommodationTypeOptions.filter(
    (type) => (selectedCatalogCity?.accommodation_type_counts?.[type] ?? 0) > 0,
  );
  const endDate = buildEndDate(form.start_date, selectedNights);
  const unusedSelectedTransportModes = form.transport_modes.filter(
    (mode) => !form.transport_by_day.includes(mode),
  );
  const hasTransportAssignmentGap = form.transport_modes.length > 1 && unusedSelectedTransportModes.length > 0;
  const hasJejuTransitDay = form.city === "jeju" && form.transport_by_day.includes("transit");

  useEffect(() => {
    if (!form.city) {
      return;
    }

    const cityStillVisible = cities.some((option) => option.city === form.city);
    if (!cityStillVisible) {
      setForm((prev) => {
        const defaultMode = defaultDayTravelMode("");
        const days = parseNights(prev.duration_label) + 1;
        return {
          ...prev,
          city: "",
          accommodation_types: [],
          transport_modes: [defaultMode],
          transport_by_day: Array.from({ length: days }, () => defaultMode),
        };
      });
    }
  }, [cities, form.city]);

  useEffect(() => {
    const previousDocHref = docDownload?.href;
    const previousPrintHref = printPreview?.href;

    if (!result) {
      setDocDownload(null);
      setPrintPreview(null);
      return () => {
        revokeItineraryExportUrl(previousDocHref);
        revokeItineraryExportUrl(previousPrintHref);
      };
    }

    const labels = {
      cityLabel: toCityLabel(result.city),
      budgetLabel: labelBudget(result.budget_band),
      styleLabel: labelStyle(result.style),
      companionLabel: labelCompanion(result.companion_type),
      conceptLabels: result.concepts.map(labelTripConcept),
      timeSlotLabel: (value: string) => labelTimeSlot(value as TimeSlot),
    };

    const nextDocDownload = createItineraryDocDownload(result, labels);
    const nextPrintPreview = createItineraryPrintPreview(result, labels);

    setDocDownload(nextDocDownload);
    setPrintPreview(nextPrintPreview);

    return () => {
      revokeItineraryExportUrl(previousDocHref);
      revokeItineraryExportUrl(previousPrintHref);
      revokeItineraryExportUrl(nextDocDownload.href);
      revokeItineraryExportUrl(nextPrintPreview.href);
    };
  }, [result]);

  const updateField = <K extends keyof PlannerFormState>(key: K, value: PlannerFormState[K]) => {
    setForm((prev) => {
      const next: PlannerFormState = { ...prev, [key]: value };

      if (key === "city") {
        const defaultMode = defaultDayTravelMode(value as string);
        const days = parseNights(prev.duration_label) + 1;
        next.accommodation_types = [];
        next.transport_modes = [defaultMode];
        next.transport_by_day = Array.from({ length: days }, () => defaultMode);
      }

      if (key === "duration_label") {
        const days = parseNights(value as string) + 1;
        next.transport_by_day = resizeTransportByDay(prev.transport_by_day, days, prev.transport_modes);
      }

      return next;
    });
  };

  const toggleAccommodationType = (type: AccommodationTypeLabel) => {
    setForm((prev) => ({
      ...prev,
      accommodation_types: prev.accommodation_types.includes(type)
        ? prev.accommodation_types.filter((item) => item !== type)
        : [...prev.accommodation_types, type],
    }));
  };

  const handleAccommodationBudgetToggle = (enabled: boolean) => {
    setIsAccommodationBudgetOn(enabled);
    if (!enabled) {
      updateField("accommodation_budget_band", null);
    }
  };

  const toggleTransportMode = (mode: DayTransportMode) => {
    setForm((prev) => {
      const days = parseNights(prev.duration_label) + 1;
      const isSelected = prev.transport_modes.includes(mode);

      if (days === 1) {
        // Only one mode chip can be active on a 1-day trip - picking the
        // other one swaps the selection instead of adding to it.
        if (isSelected) {
          return prev;
        }
        return { ...prev, transport_modes: [mode], transport_by_day: [mode] };
      }

      if (isSelected) {
        if (prev.transport_modes.length === 1) {
          // At least one mode must always stay selected.
          return prev;
        }
        const nextModes = prev.transport_modes.filter((item) => item !== mode);
        const fallback = nextModes[0];
        return {
          ...prev,
          transport_modes: nextModes,
          transport_by_day: prev.transport_by_day.map((assigned) => (assigned === mode ? fallback : assigned)),
        };
      }

      // Turning a new mode on: keep the existing day assignments, but make
      // sure the newly enabled mode is actually used somewhere (the last
      // day) rather than appearing selected with zero days assigned.
      const nextByDay = [...prev.transport_by_day];
      if (nextByDay.length > 0 && !nextByDay.includes(mode)) {
        nextByDay[nextByDay.length - 1] = mode;
      }
      return {
        ...prev,
        transport_modes: [...prev.transport_modes, mode],
        transport_by_day: nextByDay,
      };
    });
  };

  const setDayTransportMode = (dayIndex: number, mode: DayTransportMode) => {
    setForm((prev) => {
      const nextByDay = [...prev.transport_by_day];
      nextByDay[dayIndex] = mode;
      return { ...prev, transport_by_day: nextByDay };
    });
  };

  const toggleConcept = (concept: TripConcept) => {
    setForm((prev) => {
      const hasConcept = prev.concepts.includes(concept);
      const nextConcepts = hasConcept
        ? prev.concepts.filter((item) => item !== concept)
        : [...prev.concepts, concept];

      return {
        ...prev,
        concepts: nextConcepts.length > 0 ? nextConcepts : ["sightseeing"],
      };
    });
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError("");
    setMessage("");

    try {
      const { accommodation_types, accommodation_budget_band, transport_modes, ...planForm } = form;
      const response = await apiClient.post<unknown>("/rule-itinerary/generate", {
        ...planForm,
        travelers: Number(form.travelers) || 2,
        ...(accommodation_types.length > 0 ? { accommodation_types } : {}),
        ...(isAccommodationBudgetOn && accommodation_budget_band ? { accommodation_budget_band } : {}),
      });

      const nextResult = normalizeGenerateResponse(response.data);
      setResult(nextResult);
      setCurrentStep(STEP_COUNT);
      setMessage(`${toCityLabel(nextResult.city)} 기준으로 ${nextResult.items.length}개의 일정이 생성되었습니다.`);
    } catch (generateError) {
      const nextError =
        generateError instanceof Error ? generateError.message : "규칙 기반 일정 생성에 실패했습니다.";
      setResult(null);
      setError(nextError);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleEditAgain = () => {
    setResult(null);
    setMessage("");
    setError("");
    setCurrentStep(STEP_COUNT);
  };

  const handleSaveTrip = async () => {
    if (!result) {
      return;
    }

    setIsSavingTrip(true);
    setError("");

    try {
      const createdTrip = await createTrip({
        title: `${toCityLabel(result.city)} ${form.duration_label} 일정`,
        destination: result.city,
        start_date: form.start_date,
        end_date: endDate,
        budget: UNSET_TRIP_BUDGET,
        travel_style: result.style,
        companion_type: result.companion_type,
      });

      for (const item of result.items) {
        await createItineraryItem(String(createdTrip.id), {
          day_number: item.day_number,
          time_slot: item.time_slot,
          place_name: item.place_name,
          category: item.category,
          notes: item.notes,
        });
      }

      navigate(`/trips/${createdTrip.id}`);
    } catch (saveError) {
      const nextError = saveError instanceof Error ? saveError.message : "여행 저장에 실패했습니다.";
      setError(nextError);
    } finally {
      setIsSavingTrip(false);
    }
  };

  const stepLabels = ["여행지", "기본 정보", "여행 스타일", "확인 및 생성"];

  return (
    <div className="tc-root">
      <div className={`tc-shell ${hasResult ? "tc-shell-wide" : ""}`}>
        {!hasResult ? (
          <>
            <h1 className="tc-title">어떤 여행을 떠나볼까요?</h1>
            <p className="tc-subtitle">도시와 기간, 취향을 고르면 하루하루 일정을 만들어 드려요.</p>

            <div className="tc-progress">
              <span className="tc-progress-label">
                {currentStep}/{STEP_COUNT} · {stepLabels[currentStep - 1]}
              </span>
              <div
                aria-label="단계 진행"
                aria-valuemax={STEP_COUNT}
                aria-valuemin={1}
                aria-valuenow={currentStep}
                className="tc-progress-track"
                role="progressbar"
              >
                {[1, 2, 3, 4].map((step) => (
                  <span
                    aria-current={step === currentStep ? "step" : undefined}
                    className={`tc-progress-seg ${step < currentStep ? "is-done" : step === currentStep ? "is-current" : ""}`}
                    key={step}
                  />
                ))}
              </div>
            </div>

            <div className="tc-form-body">
              <div className="tc-card">
                {currentStep === 1 ? (
                  <div className="tc-stack">
                    <div>
                      <h2 className="tc-stage-title">어느 도시로 떠나시나요?</h2>
                    </div>

                    {catalogLoading ? (
                      <p className="tc-note">도시 목록을 불러오는 중입니다.</p>
                    ) : cities.length === 0 ? (
                      <p className="tc-note">표시할 도시가 없습니다.</p>
                    ) : (
                      <div className="tc-city-grid" role="radiogroup" aria-label="여행지 선택">
                        {cities.map((option) => (
                          <button
                            aria-checked={form.city === option.city}
                            className={`tc-city-card ${form.city === option.city ? "is-selected" : ""}`}
                            key={option.city}
                            onClick={() => updateField("city", option.city)}
                            role="radio"
                            type="button"
                          >
                            {toCityLabel(option.city)}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ) : null}

                {currentStep === 2 ? (
                  <div className="tc-stack">
                    <div>
                      <h2 className="tc-stage-title">기본 정보</h2>
                      <p className="tc-stage-subtitle">기간과 인원, 예산 톤을 정하면 일정 밀도가 더 자연스럽게 맞춰집니다.</p>
                    </div>

                    <div className="tc-field">
                      <span className="tc-field-label">여행 시작일</span>
                      <input
                        className="tc-date-input"
                        onChange={(event) => updateField("start_date", event.target.value)}
                        type="date"
                        value={form.start_date}
                      />
                    </div>

                    <div className="tc-field">
                      <span className="tc-field-label">여행 인원</span>
                      <div className="tc-chip-row" role="radiogroup" aria-label="여행 인원">
                        {travelerOptions.map((option) => (
                          <button
                            aria-checked={form.travelers === option.value}
                            className={`tc-chip ${form.travelers === option.value ? "is-selected" : ""}`}
                            key={option.value}
                            onClick={() => updateField("travelers", option.value)}
                            role="radio"
                            type="button"
                          >
                            {option.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="tc-field">
                      <span className="tc-field-label">여행 기간</span>
                      <div className="tc-chip-row" role="radiogroup" aria-label="여행 기간">
                        {nightsOptions.map((night) => (
                          <button
                            aria-checked={selectedNights === night}
                            className={`tc-chip ${selectedNights === night ? "is-selected" : ""}`}
                            key={night}
                            onClick={() => updateField("duration_label", buildDurationLabel(night))}
                            role="radio"
                            type="button"
                          >
                            {night}박
                          </button>
                        ))}
                      </div>
                      <p className="tc-note">
                        현재 선택: {form.duration_label} · {form.start_date} ~ {endDate}
                      </p>
                    </div>

                    <div className="tc-field">
                      <span className="tc-field-label">예산</span>
                      <div className="tc-choice-grid tc-choice-grid-3">
                        {budgetOptions.map((option) => (
                          <button
                            aria-checked={form.budget_band === option}
                            className={`tc-choice-card ${form.budget_band === option ? "is-selected" : ""}`}
                            key={option}
                            onClick={() => updateField("budget_band", option)}
                            role="radio"
                            type="button"
                          >
                            <strong>{labelBudget(option)}</strong>
                            <small>{budgetIntensityLabel(option)}</small>
                            <span>{budgetHint(option)}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    {availableAccommodationTypes.length > 0 ? (
                      <div className="tc-field">
                        <span className="tc-field-label">숙소 유형 (선택, 여러 개 가능)</span>
                        <div className="tc-chip-row">
                          {availableAccommodationTypes.map((type) => (
                            <button
                              aria-pressed={form.accommodation_types.includes(type)}
                              className={`tc-chip ${form.accommodation_types.includes(type) ? "is-selected" : ""}`}
                              key={type}
                              onClick={() => toggleAccommodationType(type)}
                              type="button"
                            >
                              {type} {selectedCatalogCity?.accommodation_type_counts?.[type]}
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    <div className="tc-field">
                      <label className="tc-toggle-row">
                        <input
                          checked={isAccommodationBudgetOn}
                          onChange={(event) => handleAccommodationBudgetToggle(event.target.checked)}
                          type="checkbox"
                        />
                        <span>숙소 예산을 따로 설정</span>
                      </label>
                      {isAccommodationBudgetOn ? (
                        <div className="tc-choice-grid tc-choice-grid-3">
                          {budgetOptions.map((option) => (
                            <button
                              aria-checked={form.accommodation_budget_band === option}
                              className={`tc-choice-card ${form.accommodation_budget_band === option ? "is-selected" : ""}`}
                              key={option}
                              onClick={() => updateField("accommodation_budget_band", option)}
                              role="radio"
                              type="button"
                            >
                              <strong>{labelBudget(option)}</strong>
                              <small>{budgetIntensityLabel(option)}</small>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <p className="tc-note">
                          숙소는 위에서 고른 활동 예산({labelBudget(form.budget_band)})을 따릅니다.
                        </p>
                      )}
                    </div>

                    <div className="tc-field">
                      <span className="tc-field-label">이동수단 (최소 1개)</span>
                      <div className="tc-chip-row">
                        {(["transit", "car"] as DayTransportMode[]).map((mode) => (
                          <button
                            aria-pressed={form.transport_modes.includes(mode)}
                            className={`tc-chip ${form.transport_modes.includes(mode) ? "is-selected" : ""}`}
                            key={mode}
                            onClick={() => toggleTransportMode(mode)}
                            type="button"
                          >
                            {labelTransportModeChoice(mode)}
                          </button>
                        ))}
                      </div>

                      {form.transport_modes.length > 1 ? (
                        <div className="tc-day-assign-list">
                          {form.transport_by_day.map((assignedMode, dayIndex) => (
                            <div className="tc-day-assign-row" key={dayIndex}>
                              <span>{dayIndex + 1}일차</span>
                              <div aria-label={`${dayIndex + 1}일차 이동수단`} className="tc-segment" role="group">
                                {form.transport_modes.map((mode) => (
                                  <button
                                    aria-pressed={assignedMode === mode}
                                    className={`tc-segment-btn ${assignedMode === mode ? "is-selected" : ""}`}
                                    key={mode}
                                    onClick={() => setDayTransportMode(dayIndex, mode)}
                                    type="button"
                                  >
                                    {labelTransportModeChoice(mode)}
                                  </button>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : null}

                      {hasTransportAssignmentGap ? (
                        <div className="tc-alert tc-alert-warning">
                          선택한 이동수단({unusedSelectedTransportModes.map(labelTransportModeChoice).join(", ")})이
                          하루도 배정되지 않았어요. 적어도 하루는 배정해야 일정을 생성할 수 있어요.
                        </div>
                      ) : null}
                      {hasJejuTransitDay ? (
                        <div className="tc-alert tc-alert-info">제주는 대중교통 이동에 시간이 오래 걸릴 수 있어요.</div>
                      ) : null}
                    </div>
                  </div>
                ) : null}

                {currentStep === 3 ? (
                  <div className="tc-stack">
                    <div>
                      <h2 className="tc-stage-title">여행 스타일</h2>
                      <p className="tc-stage-subtitle">원하는 분위기와 동행 유형에 맞춰 추천 기준을 바꿉니다.</p>
                    </div>

                    <div className="tc-field">
                      <span className="tc-field-label">관심 테마</span>
                      <div className="tc-chip-row">
                        {conceptOptions.map((concept) => (
                          <button
                            aria-pressed={form.concepts.includes(concept)}
                            className={`tc-chip ${form.concepts.includes(concept) ? "is-selected" : ""}`}
                            key={concept}
                            onClick={() => toggleConcept(concept)}
                            type="button"
                          >
                            {labelTripConcept(concept)}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="tc-field">
                      <span className="tc-field-label">일정 운영 방식</span>
                      <p className="tc-note">동선을 얼마나 촘촘하게 짤지, 이동을 어떻게 다룰지 정합니다.</p>
                      <div className="tc-choice-grid tc-choice-grid-2" role="radiogroup" aria-label="일정 운영 방식">
                        {styleOptions.map((option) => (
                          <button
                            aria-checked={form.style === option}
                            className={`tc-choice-card ${form.style === option ? "is-selected" : ""}`}
                            key={option}
                            onClick={() => updateField("style", option)}
                            role="radio"
                            type="button"
                          >
                            <strong>{labelStyle(option)}</strong>
                            <span>{labelStyleDesc(option)}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="tc-field">
                      <span className="tc-field-label">누구와 함께 가나요?</span>
                      <p className="tc-note">같은 도시라도 동행 유형에 따라 추천 장소와 페이스가 달라집니다.</p>
                      <div className="tc-choice-grid tc-choice-grid-2" role="radiogroup" aria-label="동행 유형">
                        {companionOptions.map((option) => (
                          <button
                            aria-checked={form.companion_type === option}
                            className={`tc-choice-card ${form.companion_type === option ? "is-selected" : ""}`}
                            key={option}
                            onClick={() => updateField("companion_type", option)}
                            role="radio"
                            type="button"
                          >
                            <strong>{labelCompanion(option)}</strong>
                            <span>{labelCompanionDesc(option)}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : null}

                {currentStep === 4 ? (
                  <div className="tc-stack">
                    <div>
                      <h2 className="tc-stage-title">확인 후 일정 생성</h2>
                      <p className="tc-stage-subtitle">입력한 조건을 마지막으로 확인하고 바로 생성할 수 있습니다.</p>
                    </div>

                    <div className="tc-summary-grid">
                      <div className="tc-summary-item">
                        <span className="tc-summary-label">여행지</span>
                        <span className="tc-summary-value">{form.city ? toCityLabel(form.city) : "자동 선택"}</span>
                        <span className="tc-summary-note">선택한 도시 기준으로 일정을 생성합니다.</span>
                      </div>

                      <div className="tc-summary-item">
                        <span className="tc-summary-label">기간과 인원</span>
                        <span className="tc-summary-value">
                          {form.duration_label || "2박 3일"} · {form.travelers === 5 ? "5인 이상" : `${form.travelers}명`}
                        </span>
                        <span className="tc-summary-note">일정 길이에 맞춰 하루 단위로 나눠 생성합니다.</span>
                      </div>

                      <div className="tc-summary-item">
                        <span className="tc-summary-label">예산</span>
                        <span className="tc-summary-value">{labelBudget(form.budget_band)}</span>
                        <span className="tc-summary-note">{budgetIntensityLabel(form.budget_band)}</span>
                      </div>

                      {form.accommodation_types.length > 0 ? (
                        <div className="tc-summary-item">
                          <span className="tc-summary-label">숙소 유형</span>
                          <span className="tc-summary-value">{form.accommodation_types.join(", ")}</span>
                          <span className="tc-summary-note">선택한 유형 안에서 추천합니다.</span>
                        </div>
                      ) : null}

                      {isAccommodationBudgetOn && form.accommodation_budget_band ? (
                        <div className="tc-summary-item">
                          <span className="tc-summary-label">숙소 예산</span>
                          <span className="tc-summary-value">{labelBudget(form.accommodation_budget_band)}</span>
                          <span className="tc-summary-note">{budgetIntensityLabel(form.accommodation_budget_band)}</span>
                        </div>
                      ) : null}

                      <div className="tc-summary-item">
                        <span className="tc-summary-label">스타일</span>
                        <span className="tc-summary-value">{labelStyle(form.style)}</span>
                        <span className="tc-summary-note">{form.concepts.map(labelTripConcept).join(", ")}</span>
                      </div>

                      <div className="tc-summary-item">
                        <span className="tc-summary-label">이동수단</span>
                        <span className="tc-summary-value">{summarizeTransportByDay(form.transport_by_day)}</span>
                        <span className="tc-summary-note">하루에 한 수단만 선택할 수 있어요.</span>
                      </div>
                    </div>

                    {hasTransportAssignmentGap ? (
                      <div className="tc-alert tc-alert-warning">
                        선택한 이동수단을 모두 최소 하루는 배정해야 일정을 생성할 수 있어요.
                      </div>
                    ) : null}

                    <button
                      className="tc-btn tc-btn-primary"
                      disabled={isGenerating || hasTransportAssignmentGap}
                      onClick={handleGenerate}
                      type="button"
                    >
                      {isGenerating ? "일정을 만들고 있어요…" : "일정 만들기"}
                    </button>
                  </div>
                ) : null}
              </div>

              {message ? <div className="tc-alert tc-alert-success">{message}</div> : null}
              {error ? <div className="tc-alert tc-alert-danger">{error}</div> : null}
            </div>

            <div className="tc-step-nav">
              <button
                className="tc-btn tc-btn-secondary"
                disabled={currentStep === 1}
                onClick={() => setCurrentStep((step) => Math.max(1, step - 1))}
                type="button"
              >
                이전
              </button>
              <button
                className="tc-btn tc-btn-primary"
                disabled={currentStep === STEP_COUNT || (currentStep === 1 && !form.city)}
                onClick={() => setCurrentStep((step) => Math.min(STEP_COUNT, step + 1))}
                type="button"
              >
                다음
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="tc-card tc-result-header">
              <h1 className="tc-result-title">{toCityLabel(result.city)} 일정이 준비됐어요</h1>
              <p className="tc-result-desc">
                {toCityLabel(result.city)}에서 {result.nights}박 {result.days}일 동안 {labelStyle(result.style)} 흐름으로 즐길 수 있게 정리했습니다.
              </p>
              <div className="tc-tag-row">
                <span className="tc-tag">{labelCompanion(result.companion_type)}</span>
                <span className="tc-tag">{labelBudget(result.budget_band)}</span>
                {result.concepts.map((concept) => (
                  <span className="tc-tag" key={concept}>
                    {labelTripConcept(concept)}
                  </span>
                ))}
              </div>
              <div className="tc-glance-row">
                <div className="tc-glance-item">
                  <span>추천 장소</span>
                  <strong>{result.items.length}곳</strong>
                </div>
                <div className="tc-glance-item">
                  <span>이동 권역</span>
                  <strong>{totalAreaCount}개</strong>
                </div>
                <div className="tc-glance-item">
                  <span>대표 코스</span>
                  <strong>{summarizeRoute(result.items)}</strong>
                </div>
              </div>
              <div className="tc-summary-grid" style={{ marginTop: 16 }}>
                <div className="tc-summary-item">
                  <span className="tc-summary-label">기간과 인원</span>
                  <span className="tc-summary-value">
                    {result.nights}박 {result.days}일 · {result.travelers}명
                  </span>
                </div>
                <div className="tc-summary-item">
                  <span className="tc-summary-label">동행 유형</span>
                  <span className="tc-summary-value">{labelCompanion(result.companion_type)}</span>
                </div>
              </div>
            </div>

            {result.accommodation_recommendation ? (
              <div className="tc-card">
                <p className="tc-section-label">추천 숙소</p>
                <p className="tc-section-value">{result.accommodation_recommendation.name}</p>
                <div className="tc-tag-row">
                  <span className="tc-tag">{result.accommodation_recommendation.accommodation_type}</span>
                  {result.accommodation_recommendation.checkin_time ? (
                    <span className="tc-tag">체크인 {result.accommodation_recommendation.checkin_time}</span>
                  ) : null}
                  {result.accommodation_recommendation.checkout_time ? (
                    <span className="tc-tag">체크아웃 {result.accommodation_recommendation.checkout_time}</span>
                  ) : null}
                </div>
                {result.accommodation_recommendation.average_price_krw != null ? (
                  <>
                    <p className="tc-section-note" style={{ marginTop: 10 }}>
                      1박 기준 약 {formatApproxManwon(result.accommodation_recommendation.average_price_krw)}
                    </p>
                    <p className="tc-section-note">참고 가격 · {PRICE_REFERENCE_PERIOD} 확인 · 변동될 수 있어요</p>
                  </>
                ) : null}
              </div>
            ) : null}

            {result.estimated_cost ? (
              <div className="tc-card">
                <p className="tc-section-label">예상 비용</p>
                <p className="tc-section-value">
                  {formatApproxManwonRange(result.estimated_cost.min_krw, result.estimated_cost.max_krw)}
                </p>
                <p className="tc-section-note">참고 가격 · {PRICE_REFERENCE_PERIOD} 확인 · 변동될 수 있어요</p>
                <p className="tc-section-note">
                  입장료 확인 {result.estimated_cost.priced_place_count}곳 기준 · 식당·교통비 제외
                </p>
                {result.estimated_cost.unpriced_place_count > 0 ? (
                  <p className="tc-section-note">
                    가격 미확인 {result.estimated_cost.unpriced_place_count}곳은 상한으로 가정
                  </p>
                ) : null}
                {!result.estimated_cost.accommodation_included ? (
                  <p className="tc-section-note">숙소 가격 미확인으로 숙소 비용 제외</p>
                ) : null}
              </div>
            ) : null}

            {message ? (
              <div className="tc-alert tc-alert-success" style={{ marginBottom: 16 }}>
                {message}
              </div>
            ) : null}
            {error ? (
              <div className="tc-alert tc-alert-danger" style={{ marginBottom: 16 }}>
                {error}
              </div>
            ) : null}

            <div className="tc-card">
              <h2 className="tc-stage-title">일차별 추천 동선</h2>
              <p className="tc-stage-subtitle">오전, 오후, 저녁 흐름으로 끊어서 보기 쉽게 정리했습니다.</p>
              {showTravelEstimateNotice ? (
                <div className="tc-alert tc-alert-info" style={{ marginBottom: 16 }}>
                  이동시간은 직선거리 기반 추정치예요. 실제 경로와 교통 상황에 따라 달라질 수 있어요.
                </div>
              ) : null}
              {groupedItems.map((group) => {
                const dayTravel = dayTravelByDay.get(group.day);
                const mode = dayTravelMode[group.day] ?? defaultDayTravelMode(result.city);
                const dayMeals = mealsByDay.get(group.day);
                const accommodationName = result.accommodation_recommendation?.name;
                const timelineEntries = buildDayTimelineEntries(group.items, dayMeals);
                const legByKey = new Map<string, RuleTravelLeg>();
                for (const leg of dayTravel?.legs ?? []) {
                  legByKey.set(travelLegKey(leg.from_kind, leg.from_name, leg.to_kind, leg.to_name), leg);
                }
                const firstEntry = timelineEntries[0];
                const lastEntry = timelineEntries[timelineEntries.length - 1];
                const startLeg =
                  accommodationName && firstEntry
                    ? legByKey.get(
                        travelLegKey(
                          "accommodation",
                          accommodationName,
                          dayTimelineEntryKind(firstEntry),
                          dayTimelineEntryName(firstEntry),
                        ),
                      )
                    : undefined;
                const endLeg =
                  accommodationName && lastEntry
                    ? legByKey.get(
                        travelLegKey(
                          dayTimelineEntryKind(lastEntry),
                          dayTimelineEntryName(lastEntry),
                          "accommodation",
                          accommodationName,
                        ),
                      )
                    : undefined;

                return (
                <div className="tc-day-card" key={group.day}>
                  <div className="tc-day-head">
                    <div>
                      <h3 className="tc-day-title">{group.day}일차</h3>
                      <p className="tc-day-route">{summarizeRoute(group.items)}</p>
                    </div>
                  </div>
                  {dayTravel ? (
                    <DayTravelPanel
                      dayTravel={dayTravel}
                      mode={mode}
                      onModeChange={(nextMode) =>
                        setDayTravelMode((previous) => ({ ...previous, [group.day]: nextMode }))
                      }
                    />
                  ) : null}
                  {result.day_duration_warnings
                    .filter((warning) => warning.day_number === group.day)
                    .map((warning) => (
                      <div className="tc-alert tc-alert-warning" key={`duration-warning-${warning.day_number}`} style={{ marginBottom: 12 }}>
                        {warning.message}
                      </div>
                    ))}
                  {result.closed_day_exclusions
                    .filter((exclusion) => exclusion.day_number === group.day)
                    .map((exclusion) => (
                      <div
                        className="tc-alert tc-alert-info"
                        key={`closed-day-exclusion-${exclusion.day_number}-${exclusion.place_name}`}
                        style={{ marginBottom: 12 }}
                      >
                        {exclusion.message}
                      </div>
                    ))}
                  {result.weather_alerts
                    .filter((alert) => alert.day_number === group.day)
                    .map((alert) => (
                      <WeatherBanner alert={alert} key={`weather-alert-${alert.day_number}-${alert.condition}`} />
                    ))}
                  <div className="tc-timeline">
                    {startLeg ? (
                      <TravelConnectorRow
                        label={`숙소에서 출발 · ${accommodationName}`}
                        leg={startLeg}
                        mode={mode}
                      />
                    ) : null}
                    {timelineEntries.map((entry, index) => {
                      const previousEntry = index > 0 ? timelineEntries[index - 1] : null;
                      const connectorLeg = previousEntry
                        ? legByKey.get(
                            travelLegKey(
                              dayTimelineEntryKind(previousEntry),
                              dayTimelineEntryName(previousEntry),
                              dayTimelineEntryKind(entry),
                              dayTimelineEntryName(entry),
                            ),
                          )
                        : undefined;

                      if (entry.type === "item") {
                        const item = entry.item;
                        const note = splitNoteLines(item.notes);
                        const showFallbackTravelTime = !connectorLeg && item.travel_minutes_from_previous !== null;

                        return (
                          <Fragment key={`${group.day}-${item.time_slot}-${item.place_name}`}>
                            {connectorLeg ? <TravelConnectorRow leg={connectorLeg} mode={mode} /> : null}
                            <div className="tc-stop">
                              <div className="tc-stop-time">
                                <span>{labelTimeSlot(item.time_slot)}</span>
                              </div>
                              <div className="tc-stop-body">
                                {showFallbackTravelTime ? (
                                  <p className="tc-stop-fallback-travel">
                                    이전 장소에서 약 {item.travel_minutes_from_previous}분 이동
                                  </p>
                                ) : null}
                                <div className="tc-stop-name-row">
                                  <strong className="tc-stop-name">{item.place_name}</strong>
                                  <span className="tc-stop-chip">{item.category}</span>
                                </div>
                                <p className="tc-stop-area">{item.area}</p>
                                {item.average_cost_krw != null ? (
                                  <p className="tc-stop-cost">{formatCostLabel(item.average_cost_krw)}</p>
                                ) : null}
                                {note.headline ? <p className="tc-stop-note-lead">{note.headline}</p> : null}
                                {note.details.map((line, lineIndex) => (
                                  <p key={`${item.place_name}-note-${lineIndex}`} className="tc-stop-note-line">
                                    {line}
                                  </p>
                                ))}
                              </div>
                            </div>
                          </Fragment>
                        );
                      }

                      const meal = entry.meal;
                      const showFallbackTravelTime = !connectorLeg && meal.travel_minutes_from_previous !== null;

                      return (
                        <Fragment key={`${group.day}-meal-${meal.meal_type}-${meal.place_name}`}>
                          {connectorLeg ? <TravelConnectorRow leg={connectorLeg} mode={mode} /> : null}
                          <MealCard meal={meal} showTravelTime={showFallbackTravelTime} />
                        </Fragment>
                      );
                    })}
                    {endLeg ? (
                      <TravelConnectorRow label={`숙소로 복귀 · ${accommodationName}`} leg={endLeg} mode={mode} />
                    ) : null}
                  </div>
                </div>
                );
              })}
            </div>

            <div className="tc-result-actions">
              <button className="tc-btn tc-btn-primary" disabled={isSavingTrip} onClick={handleSaveTrip} type="button">
                {isSavingTrip ? "여행 저장 중..." : "이 일정으로 여행 저장"}
              </button>
              {docDownload ? (
                <a className="tc-btn tc-btn-ghost" download={docDownload.filename} href={docDownload.href}>
                  문서 파일 다운로드
                </a>
              ) : null}
              {printPreview ? (
                <a className="tc-btn tc-btn-ghost" href={printPreview.href} rel="noreferrer" target="_blank">
                  PDF로 저장
                </a>
              ) : null}
              <button className="tc-btn tc-btn-secondary" onClick={handleEditAgain} type="button">
                조건 다시 수정하기
              </button>
              <button
                className="tc-btn tc-btn-ghost"
                onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
                type="button"
              >
                상단으로 이동
              </button>
            </div>

            {import.meta.env.DEV ? (
              <details className="tc-raw-panel">
                <summary>원본 JSON 보기 (개발 모드 전용)</summary>
                <pre>{JSON.stringify(result, null, 2)}</pre>
              </details>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
