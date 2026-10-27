// Pure, React-free logic for the "다른 추천" slot-swap feature (see the
// trip-create-form result screen). Kept separate from the component so it
// can be exercised without rendering anything - the component only ever
// calls these functions and stores their return values in local state
// (slotSwaps), never duplicates this logic inline.
//
// A swap never touches the backend response itself (`result`). It's a
// purely client-side override: "for this (day_number, time_slot), show
// this alternative's fields instead of the original item's."

export type SlotAlternative = {
  place_id: string;
  place_name: string;
  category: string;
  area: string;
  notes: string;
  average_cost_krw?: number | null;
};

// Shape every call site actually needs - RuleItineraryItem satisfies this
// structurally, so the component never has to convert anything.
export type SwappableItem = {
  day_number: number;
  time_slot: string;
  place_name: string;
  category: string;
  area: string;
  notes: string;
  average_cost_krw?: number | null;
  reasons?: unknown[];
  alternatives?: SlotAlternative[];
};

// Keyed by `${day_number}:${time_slot}` - unique within one itinerary
// response (a day has at most one item per time_slot, full-day days
// included, since each of its 3 slots still has a distinct time_slot).
export type SlotSwapMap = Record<string, SlotAlternative>;

export function buildSlotKey(dayNumber: number, timeSlot: string): string {
  return `${dayNumber}:${timeSlot}`;
}

function slotKeyForItem(item: Pick<SwappableItem, "day_number" | "time_slot">): string {
  return buildSlotKey(item.day_number, item.time_slot);
}

export function isSlotSwapped(swaps: SlotSwapMap, item: Pick<SwappableItem, "day_number" | "time_slot">): boolean {
  return slotKeyForItem(item) in swaps;
}

export function hasAnySlotSwap(swaps: SlotSwapMap): boolean {
  return Object.keys(swaps).length > 0;
}

// 교체: 이 슬롯에 이 대안을 적용한다 (불변 - 새 맵을 반환한다).
export function applySlotSwap(
  swaps: SlotSwapMap,
  item: Pick<SwappableItem, "day_number" | "time_slot">,
  alternative: SlotAlternative,
): SlotSwapMap {
  return { ...swaps, [slotKeyForItem(item)]: alternative };
}

// 되돌리기: 이 슬롯의 교체를 지운다 (없으면 같은 맵을 그대로 반환해 불필요한
// 리렌더를 피한다).
export function revertSlotSwap(swaps: SlotSwapMap, item: Pick<SwappableItem, "day_number" | "time_slot">): SlotSwapMap {
  const key = slotKeyForItem(item);
  if (!(key in swaps)) {
    return swaps;
  }
  const next = { ...swaps };
  delete next[key];
  return next;
}

export function getActiveAlternativePlaceId(
  swaps: SlotSwapMap,
  item: Pick<SwappableItem, "day_number" | "time_slot">,
): string | null {
  return swaps[slotKeyForItem(item)]?.place_id ?? null;
}

// 저장·표시에 쓸 "현재 화면에 보여야 할" 값 - 교체 중이면 대안 값으로, 아니면
// 원래 값 그대로. reasons는 교체 중이면 항상 빈 배열(원래 장소 기준이라 맞지
// 않음 - 과제 constraint).
export function getEffectiveItem<T extends SwappableItem>(item: T, swaps: SlotSwapMap): T {
  const alternative = swaps[slotKeyForItem(item)];
  if (!alternative) {
    return item;
  }
  return {
    ...item,
    place_name: alternative.place_name,
    category: alternative.category,
    area: alternative.area,
    notes: alternative.notes,
    average_cost_krw: alternative.average_cost_krw ?? null,
    reasons: [],
  };
}

function effectivePlaceName(item: SwappableItem, swaps: SlotSwapMap): string {
  return swaps[slotKeyForItem(item)]?.place_name ?? item.place_name;
}

// 한 일정(전 일차) 안에서 candidateName이 currentItem이 아닌 다른 슬롯에 이미
// 쓰이고 있는지 - 원래 추천 장소는 id가 없어 place_name 기준으로 비교한다
// (과제 constraint). 다른 슬롯의 "현재 표시값"(교체됐으면 대안 이름, 아니면
// 원래 이름)과 비교한다.
export function isAlternativeNameUsedElsewhere(
  allItems: SwappableItem[],
  swaps: SlotSwapMap,
  currentItem: Pick<SwappableItem, "day_number" | "time_slot">,
  candidateName: string,
): boolean {
  const currentKey = slotKeyForItem(currentItem);
  return allItems.some((other) => {
    if (slotKeyForItem(other) === currentKey) {
      return false;
    }
    return effectivePlaceName(other, swaps) === candidateName;
  });
}

// 타임라인(활동 슬롯 + 식사가 시간순으로 섞인 실제 화면 순서) 한 행 - 식사는
// 교체 대상이 아니라 자기 식별자가 필요 없다. 활동 행만 day_number/time_slot
// 으로 교체 여부를 조회한다.
export type TimelineRow = { kind: "item"; dayNumber: number; timeSlot: string } | { kind: "meal" };

export type TimelineTravelHint = {
  // 이 행으로 "들어오는" 이동 정보(커넥터, 폴백 "이전 장소에서 N분" 문구)가
  // 낡은 값이라 "이동 시간 재계산 안 됨"으로 바꿔야 하면 true - 이 행 자신이
  // 교체된 활동이거나(도착지가 바뀌었으니 앞에서 오는 이동정보 전체가 무효 -
  // 앞 행이 무엇이든), 바로 앞 행이 교체된 활동이면(출발지가 바뀌었으니)
  // 해당된다.
  hideIncomingTravel: boolean;
  // 활동 행의 reasons 중 code: "near_previous"(백엔드 reasons.py의
  // _near_previous_reason - "직전 장소에서 N분"/"숙소에서 N분" 두 라벨
  // 변형을 모두 이 code로 묶는다) 칩을 지워야 하면 true - 바로 앞 행이
  // 교체된 활동일 때만. "숙소에서 N분" 변형은 하루의 첫 행에만 붙는데, 첫
  // 행은 구조상 "바로 앞 행"이 있을 수 없으므로(활동 행 앞은 전날이거나
  // 없음) 이 조건에 걸리지 않는다 - 즉 이 필드는 "직전 장소에서" 라벨에만
  // 실질적으로 적용된다(라벨 문자열이 아니라 code로 구분해 더 안정적이다).
  // 이 행 자신이 교체된 활동이면 reasons 자체가 getEffectiveItem에서 이미
  // []로 비워지므로 이 필드는 그 경우엔 아무 영향이 없다.
  hidePrecedingNearPreviousReason: boolean;
};

function isTimelineRowSwapped(row: TimelineRow, swaps: SlotSwapMap): boolean {
  return row.kind === "item" && isSlotSwapped(swaps, { day_number: row.dayNumber, time_slot: row.timeSlot });
}

// 판정 기준: "활동 슬롯 배열의 이전 항목"이 아니라 "타임라인 순서상 바로 앞
// 행"(식사 포함) - rows는 화면에 실제로 그려지는 순서(buildDayTimelineEntries
// 결과와 같은 순서)여야 한다.
export function computeTimelineTravelHints(rows: TimelineRow[], swaps: SlotSwapMap): TimelineTravelHint[] {
  return rows.map((row, index) => {
    const previous = index > 0 ? rows[index - 1] : null;
    const previousSwapped = previous ? isTimelineRowSwapped(previous, swaps) : false;
    const selfSwapped = isTimelineRowSwapped(row, swaps);
    return {
      hideIncomingTravel: selfSwapped || previousSwapped,
      hidePrecedingNearPreviousReason: previousSwapped,
    };
  });
}

export type SaveItineraryItemPayload = {
  day_number: number;
  time_slot: string;
  place_name: string;
  category: string;
  notes: string;
};

// 저장 시 보낼 payload - 화면에 표시된(교체 반영된) 값 기준, 기존 5개 필드
// 형태는 그대로다(백엔드 API·payload 모양은 바꾸지 않는다 - 과제 constraint).
export function buildSaveItemsPayload(items: SwappableItem[], swaps: SlotSwapMap): SaveItineraryItemPayload[] {
  return items.map((item) => {
    const effective = getEffectiveItem(item, swaps);
    return {
      day_number: effective.day_number,
      time_slot: effective.time_slot,
      place_name: effective.place_name,
      category: effective.category,
      notes: effective.notes,
    };
  });
}
