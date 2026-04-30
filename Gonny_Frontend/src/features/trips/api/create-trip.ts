export type CreateTripPayload = {
  title?: string;
  destination: string;
  start_date: string;
  end_date: string;
  travel_style: string;
  budget: number;
  companion_type: string;
};

export type CreateTripResponse = {
  id: number;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  budget: number;
  travel_style: string;
  companion_type: string;
  created_at: string;
};

import { apiClient } from "../../../shared/api/client";

export async function createTrip(payload: CreateTripPayload) {
  const response = await apiClient.post<CreateTripResponse>("/trips", payload);
  return response.data;
}
