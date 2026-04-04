import { apiClient } from "../../../shared/api/client";
import { queryKeys } from "../../../shared/api/query-keys";
import { mockTrips } from "../../../shared/mocks/trip-data";
import { TripSummaryItem } from "../../../shared/types/domain";
import { ApiSuccessResponse } from "../../../shared/types/api";
import { TripsListResponseDto } from "../types/trips";

function mapTripSummary(dto: TripsListResponseDto["trips"][number]): TripSummaryItem {
  return {
    id: String(dto.trip_id),
    title: dto.title,
    destination: dto.destination,
    startDate: dto.start_date,
    endDate: dto.end_date,
    status: dto.status,
    budget: 0,
    companionCount: 0,
  };
}

export async function getTrips() {
  try {
    const response = await apiClient.get<ApiSuccessResponse<TripsListResponseDto>>("/trips");
    return response.data.data.trips.map(mapTripSummary);
  } catch {
    return mockTrips;
  }
}

export { queryKeys };
