import { apiClient } from "../../../shared/api/client";
import { mockDayPlans, mockTripOverview } from "../../../shared/mocks/trip-data";
import { DayPlan, TripOverview } from "../../../shared/types/domain";
import { TripDetailResponseDto } from "../types/trips";

function mapTripOverview(dto: TripDetailResponseDto): TripOverview {
  return {
    id: String(dto.id),
    title: dto.title || `${dto.destination} 여행`,
    destination: dto.destination ?? "",
    dateRangeLabel:
      dto.start_date && dto.end_date ? `${dto.start_date} - ${dto.end_date}` : mockTripOverview.dateRangeLabel,
    weatherSummary: "날씨 정보 준비 중",
    budgetLabel: `${dto.budget.toLocaleString()}원`,
    companionLabel: dto.companion_type,
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

export async function getTripDetail(tripId: string): Promise<{
  overview: TripOverview;
  dayPlans: DayPlan[];
  itineraryItems: TripDetailResponseDto["itinerary_items"];
}> {
  try {
    const response = await apiClient.get<TripDetailResponseDto>(`/trips/${tripId}`);
    return {
      overview: mapTripOverview(response.data),
      dayPlans: mapDayPlans(response.data),
      itineraryItems: response.data.itinerary_items,
    };
  } catch {
    return {
      overview: mockTripOverview,
      dayPlans: mockDayPlans,
      itineraryItems: [],
    };
  }
}
