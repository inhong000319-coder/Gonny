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

// #135 - 분할 저장된 여행의 stay 하나(이 파일 전용 - get-trip-detail.ts/
// get-trips.ts/get-shared-trip.ts 전부 자기 DTO를 이 모양으로 매핑해서
// 넘긴다, 호출부가 각자 다른 snake_case/camelCase DTO를 몰라도 되게).
export type AccommodationStayLabelInput = {
  startNight: number;
  nights: number;
  accommodationName: string;
  accommodationType: string;
};

// "N박째" / "N~M박째" - features/trip-create/utils/accommodation-stays.ts의
// formatStayNightRange와 같은 포맷(두 기능이 같은 문구를 쓰도록).
export function formatStayNightRange(startNight: number, nights: number): string {
  const endNight = startNight + nights - 1;
  return nights === 1 ? `${startNight}박째` : `${startNight}~${endNight}박째`;
}

// 여행 목록 카드 - 한 곳이면 기존과 같은 "이름(유형)", 2곳 이상이면 첫
// 숙소 뒤에 "외 N곳"을 붙인다. 숙소가 전혀 없으면 undefined(기존과 같음).
export function formatTripCardAccommodationLabel(stays: AccommodationStayLabelInput[]): string | undefined {
  if (stays.length === 0) {
    return undefined;
  }
  const first = formatAccommodationLabel({
    accommodation_name: stays[0].accommodationName,
    accommodation_type: stays[0].accommodationType,
  });
  if (stays.length === 1) {
    return first;
  }
  return `${first} 외 ${stays.length - 1}곳`;
}

// 여행 상세 헤더 뱃지 - 한 곳이면 기존과 같은 "이름(유형)", 2곳 이상이면
// 숙소 이름을 " → "로 이어붙인다(유형은 생략 - 여러 개면 뱃지가 너무
// 길어져서). 숙소가 전혀 없으면 undefined(기존과 같음).
export function formatTripHeaderAccommodationLabel(stays: AccommodationStayLabelInput[]): string | undefined {
  if (stays.length === 0) {
    return undefined;
  }
  if (stays.length === 1) {
    return formatAccommodationLabel({
      accommodation_name: stays[0].accommodationName,
      accommodation_type: stays[0].accommodationType,
    });
  }
  return stays.map((stay) => stay.accommodationName).join(" → ");
}

// 공유 페이지 - 한 곳이면 기존과 같은 단일 줄("숙소: 이름(유형)"), 2곳
// 이상이면 stay마다 "숙소 N (범위): 이름(유형)" 한 줄씩. 숙소가 전혀
// 없으면 빈 배열(기존처럼 아무 줄도 안 그림).
export function formatSharedAccommodationLines(stays: AccommodationStayLabelInput[]): string[] {
  if (stays.length === 0) {
    return [];
  }
  if (stays.length === 1) {
    const label = formatAccommodationLabel({
      accommodation_name: stays[0].accommodationName,
      accommodation_type: stays[0].accommodationType,
    });
    return label ? [`숙소: ${label}`] : [];
  }
  return stays.map((stay, index) => {
    const label =
      formatAccommodationLabel({
        accommodation_name: stay.accommodationName,
        accommodation_type: stay.accommodationType,
      }) ?? stay.accommodationName;
    return `숙소 ${index + 1} (${formatStayNightRange(stay.startNight, stay.nights)}): ${label}`;
  });
}
