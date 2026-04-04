import { apiClient } from "../../../shared/api/client";
import { mockDayPlans, mockTripOverview } from "../../../shared/mocks/trip-data";
import { DayPlan, TripOverview } from "../../../shared/types/domain";
import { ApiSuccessResponse } from "../../../shared/types/api";
import { TripDetailResponseDto } from "../types/trips";

function mapTripOverview(dto: TripDetailResponseDto): TripOverview {
  return {
    id: String(dto.trip_id),
    title: dto.title,
    destination: dto.destination ?? "",
    dateRangeLabel:
      dto.start_date && dto.end_date ? `${dto.start_date} - ${dto.end_date}` : mockTripOverview.dateRangeLabel,
    weatherSummary: dto.days.map((day) => day.weather_forecast).join(" / "),
    budgetLabel: mockTripOverview.budgetLabel,
    companionLabel: mockTripOverview.companionLabel,
  };
}

function mapDayPlans(dto: TripDetailResponseDto): DayPlan[] {
  return dto.days.map((day) => ({
    id: `day-${day.day_number}`,
    dayLabel: `Day ${day.day_number}`,
    weatherLabel: day.weather_forecast,
    totalTimeLabel: `Items ${day.items.length}`,
    items: day.items.map((item) => ({
      id: String(item.id),
      time: item.start_time,
      title: item.place_name,
      meta: `${item.duration_min} min / ${item.move_time_min} min move / ${item.transport}`,
      tip: item.ai_tip,
    })),
  }));
}

export async function getTripDetail(tripId: string): Promise<{
  overview: TripOverview;
  dayPlans: DayPlan[];
}> {
  try {
    const response = await apiClient.get<ApiSuccessResponse<TripDetailResponseDto>>(`/trips/${tripId}`);
    return {
      overview: mapTripOverview(response.data.data),
      dayPlans: mapDayPlans(response.data.data),
    };
  } catch {
    return {
      overview: mockTripOverview,
      dayPlans: mockDayPlans,
    };
  }
}
