export type CreateTripPayload = {
  title?: string;
  destination: string;
  start_date: string;
  end_date: string;
  travel_style: string;
  budget: number;
  companion_type: string;
  // 화면에 표시 중인 숙소의 id(추천 숙소 또는 대안으로 바꾼 숙소) - 서버가
  // destination의 숙소 목록에서 이름·유형을 찾아 스냅샷으로 저장한다(PR
  // #111). 생략하면 기존과 같이 숙소 없이 저장된다.
  accommodation_id?: string;
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
  // 구버전 서버 응답이나 숙소 없이 저장된 여행에서는 없거나 null.
  accommodation_id?: string | null;
  accommodation_name?: string | null;
  accommodation_type?: string | null;
};

import { apiClient } from "../../../shared/api/client";

export async function createTrip(payload: CreateTripPayload) {
  const response = await apiClient.post<CreateTripResponse>("/trips", payload);
  return response.data;
}
