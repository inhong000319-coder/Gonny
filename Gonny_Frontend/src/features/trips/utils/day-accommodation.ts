// Pure, React-free helper for the saved-trip itinerary editor
// (pages/trips/trip-detail-page.tsx) - which stay (if any) a given day
// number sleeps at. Mirrors the backend/#133 rule stated for this
// feature: "d일차 밤에 묵는 숙소는 d박째 숙소다" - night d belongs to
// whichever stay's [startNight, startNight + nights) range contains it.
// The trip's last day (nights + 1) has no night of its own, so it simply
// never matches any stay here - no separate "last day" check needed.
export function findStayForDay<T extends { startNight: number; nights: number }>(
  stays: T[],
  dayNumber: number,
): T | null {
  return stays.find((stay) => dayNumber >= stay.startNight && dayNumber < stay.startNight + stay.nights) ?? null;
}
