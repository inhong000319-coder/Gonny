import { apiClient } from "../../../shared/api/client";
import { ApiSuccessResponse } from "../../../shared/types/api";
import { LoginResponseDto } from "../types/auth";

export async function loginKakao(code: string) {
  const response = await apiClient.post<ApiSuccessResponse<LoginResponseDto>>("/auth/kakao", {
    code,
  });

  return response.data.data;
}
