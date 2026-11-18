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

// #135 결과 화면 - 숙소 카드 제목. 1박짜리는 "숙소 N · 1박째"(범위
// 하나로 충분 - "1박"과 "1박째"를 같이 적으면 중복), 2박 이상은
// "숙소 N · 2박 (2~3박째)"(며칠 머무는지와 그 구간 둘 다 의미가 달라
// 함께 적는다).
export function formatStayCardTitle(displayIndex: number, stay: AccommodationStayLike): string {
  const rangeLabel = formatStayNightRange(stay);
  return stay.nights === 1 ? `숙소 ${displayIndex} · ${rangeLabel}` : `숙소 ${displayIndex} · ${stay.nights}박 (${rangeLabel})`;
}

// #135 - 생성 결과를 저장(POST /trips)할 때 보낼 숙소 필드. stay가 2곳
// 이상이고 전부 숙소가 정해져 있으면 stays를, 아니면(기존 동작과 완전히
// 같게) accommodation_id만(숙소가 없으면 아무 키도 없음) 돌려준다 -
// accommodation_id와 stays를 동시에 보내면 서버가 422로 거부하므로 둘
// 중 하나만 돌려줘야 한다.
export function buildTripCreateAccommodationFields(
  stays: { nights: number; accommodation: { id: string } | null }[],
): { accommodation_id: string } | { stays: { nights: number; accommodation_id: string }[] } | Record<string, never> {
  if (stays.length >= 2 && stays.every((stay) => stay.accommodation !== null)) {
    return {
      stays: stays.map((stay) => ({ nights: stay.nights, accommodation_id: (stay.accommodation as { id: string }).id })),
    };
  }
  const accommodationId = stays[0]?.accommodation?.id;
  return accommodationId ? { accommodation_id: accommodationId } : {};
}
