import { apiClient } from "../../../shared/api/client";
import { TripsListItemDto } from "../types/trips";

// PATCH /trips/{id}/accommodation 응답은 백엔드의 TripResponse 모양이고
// TripsListItemDto와 필드가 1:1로 일치하므로(둘 다 이 트립 리소스의
// "얕은" 모양) 새 타입을 만들지 않고 그대로 재사용한다.
//
// stayIndex(#135)는 undefined면 요청 본문에 stay_index 키 자체를 넣지
// 않는다 - 숙소가 한 곳(또는 없음)인 여행의 기존 호출(이 인자를 안 주는
// 호출)이 보내는 본문이 이 기능 추가 전과 완전히 같아야 하기 때문이다.
export async function updateTripAccommodation(
  tripId: string,
  accommodationId: string | null,
  stayIndex?: number,
): Promise<TripsListItemDto> {
  try {
    const body: { accommodation_id: string | null; stay_index?: number } = { accommodation_id: accommodationId };
    if (stayIndex !== undefined) {
      body.stay_index = stayIndex;
    }
    const response = await apiClient.patch<TripsListItemDto>(`/trips/${tripId}/accommodation`, body);
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
