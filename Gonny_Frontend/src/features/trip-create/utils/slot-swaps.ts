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

// 이동 시간을 "재계산 안 됨"으로 표시해야 하는 슬롯인지 - 교체된 슬롯 자신
// (그 전 장소에서 여기로 오는 이동시간이 틀려짐) 또는 같은 날 바로 다음
// 시간대 슬롯(바뀐 장소에서 거기로 가는 이동시간이 틀려짐). dayItems는 한
// 일차의 항목들이고, time_slot 순서(= 배열 순서)가 이미 그 날의 실제 순서와
// 같다고 가정한다(buildDayTimelineEntries에 넘기기 전의 원본 순서).
export function shouldHideTravelMinutes(
  dayItems: SwappableItem[],
  swaps: SlotSwapMap,
  item: Pick<SwappableItem, "day_number" | "time_slot">,
): boolean {
  const index = dayItems.findIndex((candidate) => slotKeyForItem(candidate) === slotKeyForItem(item));
  if (index === -1) {
    return false;
  }
  if (isSlotSwapped(swaps, dayItems[index])) {
    return true;
  }
  const previous = index > 0 ? dayItems[index - 1] : null;
  return previous ? isSlotSwapped(swaps, previous) : false;
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
