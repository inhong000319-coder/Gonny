export type TripsListItemDto = {
  trip_id: number;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  status: "upcoming" | "ongoing" | "completed";
  thumbnail_url?: string;
};

export type TripsListResponseDto = {
  trips: TripsListItemDto[];
  total: number;
  page: number;
};

export type TripDetailItemDto = {
  id: number;
  order: number;
  place_name: string;
  place_type: string;
  start_time: string;
  duration_min: number;
  move_time_min: number;
  transport: string;
  address: string;
  estimated_cost: number;
  ai_tip: string;
};

export type TripDetailDayDto = {
  day_number: number;
  date: string;
  weather_forecast: string;
  items: TripDetailItemDto[];
};

export type TripDetailResponseDto = {
  trip_id: number;
  title: string;
  destination?: string;
  start_date?: string;
  end_date?: string;
  days: TripDetailDayDto[];
};
