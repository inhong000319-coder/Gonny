import { apiClient } from "../../../shared/api/client";

export type UpdateItineraryItemPayload = {
  day_number?: number;
  time_slot?: string;
  place_name?: string;
  category?: string;
  notes?: string | null;
};

export async function updateItineraryItem(tripId: string, itemId: number, payload: UpdateItineraryItemPayload) {
  const response = await apiClient.patch(`/trips/${tripId}/itinerary-items/${itemId}`, payload);
  return response.data;
}
