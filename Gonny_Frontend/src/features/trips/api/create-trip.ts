import { apiClient } from "../../../shared/api/client";
import { ApiSuccessResponse } from "../../../shared/types/api";

export type CreateTripPayload = {
  destination: string;
  start_date: string;
  end_date: string;
  travel_style: string[];
  budget: number;
  currency: string;
  transport_type: string;
  accommodation_type: string;
  meal_style: string[];
  companions: Array<{
    name: string;
    tags: string[];
    is_child?: boolean;
  }>;
  extra_request: string;
};

export type CreateTripResponse = {
  trip_id: number;
  title: string;
};

export async function createTrip(payload: CreateTripPayload) {
  const response = await apiClient.post<ApiSuccessResponse<CreateTripResponse>>("/trips", payload);
  return response.data.data;
}
