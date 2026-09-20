import { apiClient } from "../../../shared/api/client";

export type SharedItineraryItem = {
  id: number;
  day_number: number;
  time_slot: string;
  place_name: string;
  category: string;
  notes: string | null;
};

export type SharedTripDetail = {
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  companion_type: string;
  itinerary_items: SharedItineraryItem[];
};

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
