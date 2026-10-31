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
