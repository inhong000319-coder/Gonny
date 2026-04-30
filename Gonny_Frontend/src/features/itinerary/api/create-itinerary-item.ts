import { apiClient } from "../../../shared/api/client";

export type CreateItineraryItemPayload = {
  day_number: number;
  time_slot: string;
  place_name: string;
  category: string;
  notes?: string | null;
};

export async function createItineraryItem(tripId: string, payload: CreateItineraryItemPayload) {
  const response = await apiClient.post(`/trips/${tripId}/itinerary-items`, payload);
  return response.data;
}
