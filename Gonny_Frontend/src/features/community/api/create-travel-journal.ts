import { apiClient } from "../../../shared/api/client";
import { CreateTravelJournalPayload, TravelJournal } from "../types/community";

export async function createTravelJournal(tripId: string, payload: CreateTravelJournalPayload): Promise<TravelJournal> {
  const response = await apiClient.post<TravelJournal>(`/trips/${tripId}/community/journals`, payload);
  return response.data;
}
