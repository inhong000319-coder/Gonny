export const queryKeys = {
  me: ["me"] as const,
  trips: ["trips"] as const,
  trip: (tripId: string) => ["trip", tripId] as const,
  tripCommunity: (tripId: string) => ["trip", tripId, "community"] as const,
  communityFeed: ["community-feed"] as const,
  weather: (destination: string) => ["weather", destination] as const,
  expenses: (tripId: string) => ["expenses", tripId] as const,
  report: (tripId: string) => ["report", tripId] as const,
};
