import { apiClient } from "../../../shared/api/client";
import { ApiSuccessResponse } from "../../../shared/types/api";
import { RefreshTokenResponseDto } from "../types/auth";

export async function refreshToken(refreshTokenValue: string) {
  const response = await apiClient.post<ApiSuccessResponse<RefreshTokenResponseDto>>("/auth/refresh", {
    refresh_token: refreshTokenValue,
  });

  return response.data.data;
}
