import { apiClient } from "../../../shared/api/client";
import { TripSummaryItem } from "../../../shared/types/domain";
import { TripsListItemDto } from "../types/trips";

function resolveStatus(startDate: string, endDate: string): TripSummaryItem["status"] {
  const today = new Date().toISOString().slice(0, 10);
  if (today < startDate) {
    return "upcoming";
  }
  if (today > endDate) {
    return "completed";
  }
  return "ongoing";
}

function mapTripSummary(dto: TripsListItemDto): TripSummaryItem {
  return {
    id: String(dto.id),
    title: dto.title || `${dto.destination} 여행`,
    destination: dto.destination,
    startDate: dto.start_date,
    endDate: dto.end_date,
    status: resolveStatus(dto.start_date, dto.end_date),
    budget: dto.budget,
    companionCount: dto.companion_type === "family" ? 4 : dto.companion_type === "friend" ? 2 : 1,
    isFavorite: dto.is_favorite ?? false,
  };
}

// /trips는 실제로 존재하고 정상 작동하는 엔드포인트다 - 실패는 "기능
// 없음"이 아니라 일시적 네트워크 문제일 가능성이 높으므로, 가짜
// 목록으로 조용히 폴백하지 않고 실패를 그대로 던진다 (TripsPage가
// isError를 보고 재시도 버튼을 보여줌).
export async function getTrips() {
  const response = await apiClient.get<TripsListItemDto[]>("/trips");
  return response.data.map(mapTripSummary);
}
