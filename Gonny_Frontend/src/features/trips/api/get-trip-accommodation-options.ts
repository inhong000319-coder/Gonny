import { apiClient } from "../../../shared/api/client";
import { TripAccommodationOptionDto } from "../types/trips";

export async function getTripAccommodationOptions(tripId: string): Promise<TripAccommodationOptionDto[]> {
  try {
    const response = await apiClient.get<TripAccommodationOptionDto[]>(`/trips/${tripId}/accommodation-options`);
    return response.data;
  } catch (error) {
    const message =
      typeof error === "object" &&
      error !== null &&
      "response" in error &&
      typeof (error as { response?: { data?: { detail?: string } } }).response?.data?.detail === "string"
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : "숙소 후보를 불러오지 못했어요.";
    throw new Error(message);
  }
}
