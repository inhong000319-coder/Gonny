import { apiClient } from "../../../shared/api/client";
import { TripsListItemDto } from "../types/trips";

// PATCH /trips/{id}/accommodation 응답은 백엔드의 TripResponse 모양이고
// TripsListItemDto와 필드가 1:1로 일치하므로(둘 다 이 트립 리소스의
// "얕은" 모양) 새 타입을 만들지 않고 그대로 재사용한다.
export async function updateTripAccommodation(
  tripId: string,
  accommodationId: string | null,
): Promise<TripsListItemDto> {
  try {
    const response = await apiClient.patch<TripsListItemDto>(`/trips/${tripId}/accommodation`, {
      accommodation_id: accommodationId,
    });
    return response.data;
  } catch (error) {
    const message =
      typeof error === "object" &&
      error !== null &&
      "response" in error &&
      typeof (error as { response?: { data?: { detail?: string } } }).response?.data?.detail === "string"
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : "숙소 변경에 실패했어요.";
    throw new Error(message);
  }
}
