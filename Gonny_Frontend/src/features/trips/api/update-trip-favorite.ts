import { apiClient } from "../../../shared/api/client";
import { TripsListItemDto } from "../types/trips";

export async function updateTripFavorite(tripId: string, isFavorite: boolean) {
  try {
    const response = await apiClient.patch<TripsListItemDto>(`/trips/${tripId}/favorite`, {
      is_favorite: isFavorite,
    });
    return response.data;
  } catch (error) {
    const message =
      typeof error === "object" &&
      error !== null &&
      "response" in error &&
      typeof (error as { response?: { data?: { detail?: string } } }).response?.data?.detail === "string"
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : "즐겨찾기 변경 중 문제가 생겼어요.";
    throw new Error(message);
  }
}
