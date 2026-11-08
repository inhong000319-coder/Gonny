export type TripsListItemDto = {
  id: number;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  budget: number;
  travel_style: string;
  companion_type: string;
  is_favorite: boolean;
  created_at: string;
  // 구버전 응답이나 숙소 없이 저장된 여행에서는 없거나 null. 이번 작업
  // 범위상 여행 목록 페이지에는 표시하지 않는다 - 타입만 맞춘다.
  accommodation_id?: string | null;
  accommodation_name?: string | null;
  accommodation_type?: string | null;
};

// GET /trips/{id}/accommodation-options 항목 (PR #113) - 좌표·편의시설
// 등은 없음(선택 목록용으로 일부러 좁힌 응답). 정렬은 서버가
// (accommodation_type, area, name) 순으로 고정해서 보낸다.
export type TripAccommodationOptionDto = {
  id: string;
  name: string;
  accommodation_type: string;
  area: string;
  average_price_krw: number | null;
};

export type TripDetailItemDto = {
  id: number;
  trip_id: number;
  day_number: number;
  time_slot: string;
  place_name: string;
  category: string;
  notes?: string | null;
};

export type TripDetailResponseDto = {
  id: number;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  budget: number;
  travel_style: string;
  companion_type: string;
  is_favorite: boolean;
  itinerary_items: TripDetailItemDto[];
  created_at: string;
  // 구버전 응답이나 숙소 없이 저장된 여행에서는 없거나 null.
  accommodation_id?: string | null;
  accommodation_name?: string | null;
  accommodation_type?: string | null;
};
