// "이름(유형)" 형태로 미리 포맷된 숙소 표시 라벨 - 여행 상세 헤더
// (api/get-trip-detail.ts)와 여행 목록 카드(api/get-trips.ts) 둘 다 이
// 한 곳만 쓴다(표시 형식이 두 화면에서 어긋나지 않도록 하나로 모음).
// accommodation_name이 없거나 빈 문자열이면(숙소 없이 저장된 여행,
// 구버전 응답 포함) undefined를 돌려줘 호출부가 아무것도 그리지 않게
// 한다.
export function formatAccommodationLabel(trip: {
  accommodation_name?: string | null;
  accommodation_type?: string | null;
}): string | undefined {
  if (!trip.accommodation_name) {
    return undefined;
  }
  return trip.accommodation_type ? `${trip.accommodation_name}(${trip.accommodation_type})` : trip.accommodation_name;
}
