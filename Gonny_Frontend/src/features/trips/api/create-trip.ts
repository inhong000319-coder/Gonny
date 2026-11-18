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
  // #111). 생략하면 기존과 같이 숙소 없이 저장된다. #135 분할 저장(stays)
  // 과는 동시에 보내지 않는다(서버가 422).
  accommodation_id?: string;
  // #135 - 숙소가 2곳 이상인 결과를 저장할 때만 쓴다(accommodation_id
  // 대신). nights 합은 여행 전체 박수와 같아야 하고, 서버가
  // accommodation_split.allowed_partitions로 분할 자체를 다시 검증한다.
  stays?: { nights: number; accommodation_id: string }[];
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
