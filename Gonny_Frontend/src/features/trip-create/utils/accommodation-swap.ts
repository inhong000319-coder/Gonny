// Pure, React-free logic for the "다른 숙소" accommodation-swap feature
// (see the trip-create-form result screen's accommodation card). Kept
// separate from slot-swaps.ts (the activity-slot swap feature) - the two
// are independent concerns that happen to both feed the same "이동 시간
// 재계산 안 됨" presentation and the same "장소를 바꾼 일정은..." banner,
// but neither reads the other's state.
import { formatApproxManwon } from "../../../shared/pricing";

export type AccommodationAlternative = {
  id: string;
  name: string;
  accommodation_type: string;
  checkin_time?: string | null;
  checkout_time?: string | null;
  average_price_krw?: number | null;
};

// There is exactly one accommodation for the whole trip (this MVP's scope -
// see the backend's _recommend_accommodation docstring), so unlike
// SlotSwapMap (one entry per day/time_slot), this is a single optional
// value: null means "showing the original recommendation", any other value
// is the alternative currently swapped in.
export type AccommodationSwapState = AccommodationAlternative | null;

export function isAccommodationSwapped(state: AccommodationSwapState): boolean {
  return state !== null;
}

// 화면에 보여줄 "현재 숙소" 값 - 교체 중이면 대안, 아니면 원래 추천 그대로.
export function getEffectiveAccommodation<T extends AccommodationAlternative>(
  original: T,
  state: AccommodationSwapState,
): AccommodationAlternative {
  return state ?? original;
}

// 숙소 출발/복귀 커넥터(TravelConnectorRow) 자리에 그 대신 "이동 시간
// 재계산 안 됨"을 보여줘야 하는지 - 숙소 자체가 바뀌었거나(경계 양쪽
// 전부, 앞/뒤 어느 행이 닿아있든), 그 경계에 닿는 활동 자신이 교체됐으면
// (기존 활동 슬롯 교체 규칙 - slot-swaps.ts의 "자신으로 들어오는 이동
// 정보는 앞 행이 무엇이든 숨긴다"는 원칙과 동일) 해당 경계 레그는 낡은
// 값이다. 둘 중 활동 쪽만 해당하면(숙소는 그대로) 그 "재계산 안 됨"은
// 이미 활동 교체 쪽 렌더링(타임라인 루프의 hideIncomingTravel, 또는
// 기존 lastRowSwapped 처리)이 그리므로, 여기서 추가로 그리면 중복된다 -
// 그래서 호출부는 "활동 쪽이 이미 그리는 경우"를 별도로 제외하고 써야
// 한다(아래 두 함수 각각의 docstring 참고).
function accommodationBoundaryLegStale(accommodationSwapped: boolean, boundaryActivitySwapped: boolean): boolean {
  return accommodationSwapped || boundaryActivitySwapped;
}

// 숙소에서 "출발"하는 첫 커넥터 - 타임라인 루프의 index 0 처리는 활동이
// 바뀌었을 때만 자기 몫의 "재계산 안 됨"을 그린다(숙소 커넥터 자체는
// 루프 밖에서 따로 그려지기 때문에 루프는 숙소 교체를 모른다). 그래서
// 여기서 보여줄 전용 "재계산 안 됨"은 "숙소가 바뀌었고, 그 활동 자신은
// 안 바뀐" 경우에만 필요하다 - 활동도 같이 바뀌었으면 루프가 이미
// 그리므로 여기서는 숨긴다(중복 방지).
export function shouldShowAccommodationStartLegStale(
  accommodationSwapped: boolean,
  firstRowActivitySwapped: boolean,
): boolean {
  return accommodationSwapped && !firstRowActivitySwapped;
}

// 실제 커넥터(TravelConnectorRow)를 보여줘도 되는지 - 숙소/첫 활동 둘 다
// 안 바뀐 경우만. (둘 중 하나라도 바뀌면 숨기고, 위 두 "stale" 함수 중
// 하나가 대신 그린다.)
export function shouldHideAccommodationBoundaryConnector(
  accommodationSwapped: boolean,
  boundaryActivitySwapped: boolean,
): boolean {
  return accommodationBoundaryLegStale(accommodationSwapped, boundaryActivitySwapped);
}

// 숙소로 "복귀"하는 마지막 커넥터 자리의 "재계산 안 됨" - 이 자리는
// 타임라인 루프가 전혀 건드리지 않는 자리(루프는 "안으로 들어오는" 레그만
// 다루고, 마지막 행에서 "나가는" 레그는 이 함수 하나가 유일하게 그린다)
// 라서 활동/숙소 어느 쪽이 바뀌어도 그냥 OR로 합쳐도 중복이 안 생긴다.
export function shouldShowAccommodationEndLegStale(
  accommodationSwapped: boolean,
  lastRowActivitySwapped: boolean,
): boolean {
  return accommodationBoundaryLegStale(accommodationSwapped, lastRowActivitySwapped);
}

// 하루 첫 활동 항목의 "숙소에서 N분" reason 칩(code: "near_previous",
// 백엔드 reasons.py의 _near_previous_reason이 accommodation_label=True일
// 때 만드는 라벨)을 숨겨야 하는지 - 숙소가 교체됐고 이 항목이 그 날의
// 첫 "활동" 항목일 때만. "그 날의 맨 처음 보이는 행"이 아니라 "맨 처음
// 활동 항목" 기준이다 - 아침 식사가 타임라인에서 활동보다 먼저 그려질
// 수 있어서 둘이 다를 수 있다(호출부는 timelineEntries.find(e => e.type
// === "item")으로 그 날의 첫 활동 항목을 따로 찾아 비교해야 한다).
export function shouldHideAccommodationNearPreviousReason(
  isFirstActivityOfDay: boolean,
  accommodationSwapped: boolean,
): boolean {
  return isFirstActivityOfDay && accommodationSwapped;
}

// 일차 이동 합계(DayTravelPanel의 transit/car_total_minutes, day_summaries
// 의 travel_minutes) - 백엔드 _build_day_travel이 매 일차 레그 목록에
// 숙소 출발/복귀 구간을 포함시켜 합산하므로(확인한 사실 - 숙소가 있으면
// expected_leg_count에 +2, nodes 배열 양 끝에 accommodation_node를
// 넣는다), 숙소가 바뀌면 이 합계도 낡은 값이다. 숙소가 없는 일정이면
// 애초에 교체할 숙소가 없어 accommodationSwapped가 true일 수 없으므로
// 별도 분기가 필요 없다.
export function shouldHideDayTravelTotal(accommodationSwapped: boolean): boolean {
  return accommodationSwapped;
}

export function formatAccommodationAlternativePriceLabel(averagePriceKrw: number | null | undefined): string {
  if (averagePriceKrw == null) {
    return "가격 정보 없음";
  }
  return `1박 약 ${formatApproxManwon(averagePriceKrw)}`;
}
