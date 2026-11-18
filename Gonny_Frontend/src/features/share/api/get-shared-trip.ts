import { apiClient } from "../../../shared/api/client";

export type SharedItineraryItem = {
  id: number;
  day_number: number;
  time_slot: string;
  place_name: string;
  category: string;
  notes: string | null;
};

// #135 - 분할 저장된 여행의 숙소 구역 하나.
export type SharedTripStay = {
  stay_index: number;
  start_night: number;
  nights: number;
  accommodation_name: string;
  accommodation_type: string;
};

export type SharedTripDetail = {
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  companion_type: string;
  itinerary_items: SharedItineraryItem[];
  // 숙소 없이 저장된 여행(구버전 응답 포함)에서는 없거나 null. #135 이후로
  // 항상 stays[0]과 같은 값 - 단일 숙소 화면은 여전히 이 두 필드만 본다.
  accommodation_name: string | null;
  accommodation_type: string | null;
  // 없으면(구버전 응답) [] 취급.
  stays: SharedTripStay[];
};

function isSharedTripStay(value: unknown): value is SharedTripStay {
  if (!value || typeof value !== "object") {
    return false;
  }

  const stay = value as Record<string, unknown>;
  return (
    typeof stay.stay_index === "number" &&
    typeof stay.start_night === "number" &&
    typeof stay.nights === "number" &&
    typeof stay.accommodation_name === "string" &&
    typeof stay.accommodation_type === "string"
  );
}

function isSharedItineraryItem(value: unknown): value is SharedItineraryItem {
  if (!value || typeof value !== "object") {
    return false;
  }

  const item = value as Record<string, unknown>;
  return (
    typeof item.id === "number" &&
    typeof item.day_number === "number" &&
    typeof item.time_slot === "string" &&
    typeof item.place_name === "string" &&
    typeof item.category === "string"
  );
}

function normalizeSharedTripDetail(payload: unknown): SharedTripDetail {
  if (!payload || typeof payload !== "object") {
    throw new Error("공유된 일정 응답 형식이 올바르지 않습니다.");
  }

  const data = payload as Partial<SharedTripDetail>;
  if (typeof data.title !== "string" || typeof data.destination !== "string") {
    throw new Error("공유된 일정 응답 형식이 올바르지 않습니다.");
  }

  return {
    title: data.title,
    destination: data.destination,
    start_date: typeof data.start_date === "string" ? data.start_date : "",
    end_date: typeof data.end_date === "string" ? data.end_date : "",
    companion_type: typeof data.companion_type === "string" ? data.companion_type : "",
    itinerary_items: Array.isArray(data.itinerary_items) ? data.itinerary_items.filter(isSharedItineraryItem) : [],
    accommodation_name: typeof data.accommodation_name === "string" ? data.accommodation_name : null,
    accommodation_type: typeof data.accommodation_type === "string" ? data.accommodation_type : null,
    stays: Array.isArray(data.stays) ? data.stays.filter(isSharedTripStay) : [],
  };
}

// GET /share/{token} genuinely 404s for an expired/unknown token - that's
// not a "feature not built yet" 404 like some other endpoints in this
// app, so the caller should let this throw and show an honest "link
// invalid/expired" state rather than any mock fallback.
export async function getSharedTrip(token: string): Promise<SharedTripDetail> {
  const response = await apiClient.get<unknown>(`/share/${token}`);
  return normalizeSharedTripDetail(response.data);
}
