import { apiClient } from "../../../shared/api/client";
import { ApiSuccessResponse } from "../../../shared/types/api";
import { MeResponseDto } from "../types/auth";

export async function getMe() {
  const response = await apiClient.get<ApiSuccessResponse<MeResponseDto>>("/users/me");
  return response.data.data;
}
