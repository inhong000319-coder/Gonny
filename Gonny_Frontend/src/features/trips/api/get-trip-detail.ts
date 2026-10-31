import { apiClient } from "../../../shared/api/client";
import { DayPlan, TripOverview } from "../../../shared/types/domain";
import { TripDetailResponseDto } from "../types/trips";

// 숙소 없이 저장된 여행(구버전 응답 포함)에서는 accommodation_name이
// 없거나 null이다 - 그 경우 undefined를 돌려줘 호출부가 아무것도
// 그리지 않게 한다(빈 카드/문구 없이 조용히 생략 - 과제 constraint).
function formatAccommodationLabel(dto: TripDetailResponseDto): string | undefined {
  if (!dto.accommodation_name) {
    return undefined;
  }
  return dto.accommodation_type ? `${dto.accommodation_name}(${dto.accommodation_type})` : dto.accommodation_name;
}

function mapTripOverview(dto: TripDetailResponseDto): TripOverview {
  return {
    id: String(dto.id),
    title: dto.title || `${dto.destination} 여행`,
    destination: dto.destination ?? "",
    dateRangeLabel: dto.start_date && dto.end_date ? `${dto.start_date} - ${dto.end_date}` : "기간 미정",
    weatherSummary: "날씨 정보 준비 중",
    budgetLabel: `${dto.budget.toLocaleString()}원`,
    companionLabel: dto.companion_type,
    accommodationLabel: formatAccommodationLabel(dto),
  };
}

function mapDayPlans(dto: TripDetailResponseDto): DayPlan[] {
  const grouped = dto.itinerary_items.reduce<Record<number, TripDetailResponseDto["itinerary_items"]>>((acc, item) => {
    if (!acc[item.day_number]) {
      acc[item.day_number] = [];
    }
    acc[item.day_number].push(item);
    return acc;
  }, {});

  return Object.entries(grouped)
    .sort(([left], [right]) => Number(left) - Number(right))
    .map(([dayNumber, items]) => ({
      id: `day-${dayNumber}`,
      dayLabel: `${dayNumber}일차`,
      weatherLabel: "직접 수정 가능",
      totalTimeLabel: `일정 ${items.length}개`,
      items: items.map((item) => ({
        id: String(item.id),
        time: item.time_slot,
        title: item.place_name,
        meta: item.category,
        tip: item.notes ?? "",
      })),
    }));
}

// /trips/{tripId}는 실제로 존재하고 정상 작동하는 엔드포인트다 -
// get-trips.ts와 같은 성격이므로 실패를 그대로 던진다 (가짜 여행
// 정보로 조용히 폴백하지 않는다). 화면들은 isError를 보고 재시도
// 버튼을 보여준다.
export async function getTripDetail(tripId: string): Promise<{
  overview: TripOverview;
  dayPlans: DayPlan[];
  itineraryItems: TripDetailResponseDto["itinerary_items"];
}> {
  const response = await apiClient.get<TripDetailResponseDto>(`/trips/${tripId}`);
  return {
    overview: mapTripOverview(response.data),
    dayPlans: mapDayPlans(response.data),
    itineraryItems: response.data.itinerary_items,
  };
}
