import { apiClient } from "../../../shared/api/client";

export type Season = "spring" | "summer" | "autumn" | "winter";

export type FestivalItem = {
  title: string;
  city: string;
  start_date: string;
  end_date: string;
  address: string | null;
  image_url: string | null;
};

export type PopularDestinationItem = {
  title: string;
  city: string;
  address: string | null;
  image_url: string | null;
};

export type SeasonalFeedResponse = {
  season: Season;
  festivals: FestivalItem[];
  popular_destinations: PopularDestinationItem[];
};

function isSeason(value: unknown): value is Season {
  return value === "spring" || value === "summer" || value === "autumn" || value === "winter";
}

function isFestivalItem(value: unknown): value is FestivalItem {
  if (!value || typeof value !== "object") {
    return false;
  }

  const item = value as Record<string, unknown>;
  return (
    typeof item.title === "string" &&
    typeof item.city === "string" &&
    typeof item.start_date === "string" &&
    typeof item.end_date === "string"
  );
}

function isPopularDestinationItem(value: unknown): value is PopularDestinationItem {
  if (!value || typeof value !== "object") {
    return false;
  }

  const item = value as Record<string, unknown>;
  return typeof item.title === "string" && typeof item.city === "string";
}

function normalizeSeasonalFeedResponse(payload: unknown): SeasonalFeedResponse {
  if (!payload || typeof payload !== "object") {
    throw new Error("시즌 정보 응답 형식이 올바르지 않습니다.");
  }

  const data = payload as Partial<SeasonalFeedResponse>;
  return {
    season: isSeason(data.season) ? data.season : "spring",
    festivals: Array.isArray(data.festivals) ? data.festivals.filter(isFestivalItem) : [],
    popular_destinations: Array.isArray(data.popular_destinations)
      ? data.popular_destinations.filter(isPopularDestinationItem)
      : [],
  };
}

export async function getSeasonalFeed(): Promise<SeasonalFeedResponse> {
  const response = await apiClient.get<unknown>("/seasonal-feed");
  return normalizeSeasonalFeedResponse(response.data);
}
