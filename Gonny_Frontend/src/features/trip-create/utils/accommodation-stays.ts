// Pure, React-free logic for mapping a trip's days onto its (possibly
// multiple) accommodation stays - see the backend's #133
// services/accommodation_split.py day/night mapping, which this mirrors
// exactly: night n belongs to whichever stay's [start_night, start_night +
// nights) range contains it; day d's first leg uses night max(d-1, 1)'s
// stay, its last leg uses night min(d, totalNights)'s stay. A single-stay
// trip (stays.length === 1) always resolves both ends of every day to
// that one stay, reproducing the pre-split behavior exactly.

export type AccommodationStayLike = {
  stay_index: number;
  start_night: number;
  nights: number;
};

function findStayForNight<T extends AccommodationStayLike>(stays: T[], night: number): T | null {
  return stays.find((stay) => night >= stay.start_night && night < stay.start_night + stay.nights) ?? null;
}

// For day `dayNumber` of a trip with `totalNights` nights, which stay (if
// any - a trip with zero accommodation data resolves both to null) backs
// the day's first leg (from the accommodation to the day's first stop)
// and which backs its last leg (from the day's last stop back to an
// accommodation). The two differ exactly on a checkout day.
export function getDayAccommodationStays<T extends AccommodationStayLike>(
  stays: T[],
  totalNights: number,
  dayNumber: number,
): { start: T | null; end: T | null } {
  const startNight = Math.max(dayNumber - 1, 1);
  const endNight = Math.min(dayNumber, totalNights);
  return {
    start: findStayForNight(stays, startNight),
    end: findStayForNight(stays, endNight),
  };
}

// "N박째" (nights === 1) or "N~M박째" (nights > 1) - the stay's own span
// within the trip, for its card heading.
export function formatStayNightRange(stay: AccommodationStayLike): string {
  const from = stay.start_night;
  const to = stay.start_night + stay.nights - 1;
  return stay.nights === 1 ? `${from}박째` : `${from}~${to}박째`;
}
