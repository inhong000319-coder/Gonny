import { apiClient } from "../../../shared/api/client";
import { ApiSuccessResponse } from "../../../shared/types/api";
import { LoginResponseDto } from "../types/auth";

export async function loginGoogle(idToken: string) {
  const response = await apiClient.post<ApiSuccessResponse<LoginResponseDto>>("/auth/google", {
    id_token: idToken,
  });

  return response.data.data;
}
