import { apiClient } from "../../../shared/api/client";
import { mockTrips } from "../../../shared/mocks/trip-data";
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

export async function getTrips() {
  try {
    const response = await apiClient.get<TripsListItemDto[]>("/trips");
    return response.data.map(mapTripSummary);
  } catch {
    return mockTrips;
  }
}
