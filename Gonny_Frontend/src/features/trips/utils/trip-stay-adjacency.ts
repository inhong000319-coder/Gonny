// Pure, React-free helper for AccommodationChangePanel (#135) - which
// accommodation ids are already used by the stays immediately before/
// after a given one, so its candidate picker can keep the user from even
// selecting a choice the server would reject with 422 ("인접한 stay와
// 같은 숙소로 바꿀 수 없습니다").
export function getAdjacentAccommodationIds(
  stays: { accommodationId: string }[],
  stayIndex: number,
): string[] {
  const ids: string[] = [];
  const previous = stays[stayIndex - 1];
  const next = stays[stayIndex + 1];
  if (previous) {
    ids.push(previous.accommodationId);
  }
  if (next) {
    ids.push(next.accommodationId);
  }
  return ids;
}
