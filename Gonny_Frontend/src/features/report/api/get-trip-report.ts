import { apiClient } from "../../../shared/api/client";

export type TripCategoryBreakdown = {
  category: string;
  amount_krw: number;
};

export type TripReport = {
  ready: boolean;
  message: string | null;
  total_spent: number | null;
  budget: number | null;
  budget_diff_pct: number | null;
  category_breakdown: TripCategoryBreakdown[];
  visited_count: number | null;
  // null ("정보 없음") whenever fewer than 2 consecutive itinerary items
  // could be matched to catalog coordinates - see the backend's
  // _compute_trip_distance(). Never fabricated as 0km.
  distance_km: number | null;
  matched_place_count: number;
  total_place_count: number;
  insights: string[];
  satisfaction_rating: number | null;
  retrospective_note: string | null;
};

function isTripCategoryBreakdown(value: unknown): value is TripCategoryBreakdown {
  if (!value || typeof value !== "object") {
    return false;
  }

  const item = value as Record<string, unknown>;
  return typeof item.category === "string" && typeof item.amount_krw === "number";
}

function normalizeTripReport(payload: unknown): TripReport {
  if (!payload || typeof payload !== "object") {
    throw new Error("여행 회고 응답 형식이 올바르지 않습니다.");
  }

  const data = payload as Partial<TripReport>;
  if (typeof data.ready !== "boolean") {
    throw new Error("여행 회고 응답 형식이 올바르지 않습니다.");
  }

  return {
    ready: data.ready,
    message: typeof data.message === "string" ? data.message : null,
    total_spent: typeof data.total_spent === "number" ? data.total_spent : null,
    budget: typeof data.budget === "number" ? data.budget : null,
    budget_diff_pct: typeof data.budget_diff_pct === "number" ? data.budget_diff_pct : null,
    category_breakdown: Array.isArray(data.category_breakdown)
      ? data.category_breakdown.filter(isTripCategoryBreakdown)
      : [],
    visited_count: typeof data.visited_count === "number" ? data.visited_count : null,
    distance_km: typeof data.distance_km === "number" ? data.distance_km : null,
    matched_place_count: typeof data.matched_place_count === "number" ? data.matched_place_count : 0,
    total_place_count: typeof data.total_place_count === "number" ? data.total_place_count : 0,
    insights: Array.isArray(data.insights) ? data.insights.filter((item): item is string => typeof item === "string") : [],
    satisfaction_rating: typeof data.satisfaction_rating === "number" ? data.satisfaction_rating : null,
    retrospective_note: typeof data.retrospective_note === "string" ? data.retrospective_note : null,
  };
}

// GET /trips/{tripId}/report always resolves 200 (ready:false covers the
// "trip hasn't ended yet" case) - a thrown error here means a genuine
// network/server failure, not "not ready", so callers should treat it
// the same as the other real-endpoint failures in this app (isError +
// retry), not a silent mock fallback.
export async function getTripReport(tripId: string): Promise<TripReport> {
  const response = await apiClient.get<unknown>(`/trips/${tripId}/report`);
  return normalizeTripReport(response.data);
}
