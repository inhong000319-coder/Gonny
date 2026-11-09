// Pure, React-free logic for "which timeline rows show a stale ('이동 시간
// 재계산 안 됨') travel indicator" - shared by the activity-slot swap
// feature (slot-swaps.ts) and the meal swap feature (meal-swaps.ts). Lives
// in its own module rather than either of theirs so neither swap module
// has to import the other.
import { isSlotSwapped, type SlotSwapMap } from "./slot-swaps";
import { isMealSwapped, type MealSwapMap } from "./meal-swaps";

// 타임라인(활동 슬롯 + 식사가 시간순으로 섞인 실제 화면 순서) 한 행 - 각
// kind가 교체 여부를 조회할 수 있는 자기 식별자(day_number + time_slot 또는
// day_number + meal_type)를 갖는다.
export type TimelineRow =
  | { kind: "item"; dayNumber: number; timeSlot: string }
  | { kind: "meal"; dayNumber: number; mealType: string };

export type TimelineTravelHint = {
  // 이 행으로 "들어오는" 이동 정보(커넥터, 폴백 "이전 장소에서 N분" 문구)가
  // 낡은 값이라 "이동 시간 재계산 안 됨"으로 바꿔야 하면 true - 이 행 자신이
  // 교체된 활동/식사이거나(도착지가 바뀌었으니 앞에서 오는 이동정보 전체가
  // 무효 - 앞 행이 무엇이든), 바로 앞 행이 교체된 활동/식사면(출발지가
  // 바뀌었으니) 해당된다.
  hideIncomingTravel: boolean;
  // 활동/식사 행의 reasons 중 code: "near_previous"(백엔드 reasons.py의
  // _near_previous_reason - "직전 장소에서 N분"/"숙소에서 N분" 두 라벨
  // 변형을 모두 이 code로 묶는다) 칩을 지워야 하면 true - 바로 앞 행이
  // 교체된 활동/식사일 때만. "숙소에서 N분" 변형은 하루의 첫 "활동" 행에만
  // 붙는데, 첫 행은 구조상 "바로 앞 행"이 있을 수 없으므로 이 조건에 걸리지
  // 않는다 - 즉 이 필드는 "직전 장소에서" 라벨에만 실질적으로 적용된다
  // (라벨 문자열이 아니라 code로 구분해 더 안정적이다). 이 행 자신이
  // 교체됐으면 reasons 자체가 getEffectiveItem/getEffectiveMeal에서 이미
  // []로 비워지므로 이 필드는 그 경우엔 아무 영향이 없다.
  hidePrecedingNearPreviousReason: boolean;
};

function isTimelineRowSwapped(row: TimelineRow, slotSwaps: SlotSwapMap, mealSwaps: MealSwapMap): boolean {
  if (row.kind === "item") {
    return isSlotSwapped(slotSwaps, { day_number: row.dayNumber, time_slot: row.timeSlot });
  }
  return isMealSwapped(mealSwaps, { day_number: row.dayNumber, meal_type: row.mealType });
}

// 판정 기준: "활동 슬롯 배열의 이전 항목"이 아니라 "타임라인 순서상 바로 앞
// 행"(식사 포함) - rows는 화면에 실제로 그려지는 순서(buildDayTimelineEntries
// 결과와 같은 순서)여야 한다.
export function computeTimelineTravelHints(
  rows: TimelineRow[],
  slotSwaps: SlotSwapMap,
  mealSwaps: MealSwapMap,
): TimelineTravelHint[] {
  return rows.map((row, index) => {
    const previous = index > 0 ? rows[index - 1] : null;
    const previousSwapped = previous ? isTimelineRowSwapped(previous, slotSwaps, mealSwaps) : false;
    const selfSwapped = isTimelineRowSwapped(row, slotSwaps, mealSwaps);
    return {
      hideIncomingTravel: selfSwapped || previousSwapped,
      hidePrecedingNearPreviousReason: previousSwapped,
    };
  });
}
