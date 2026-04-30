import { apiClient } from "../../../shared/api/client";

export async function deleteItineraryItem(tripId: string, itemId: number) {
  await apiClient.delete(`/trips/${tripId}/itinerary-items/${itemId}`);
}
