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
};
