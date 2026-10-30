// Pure, React-free logic for assembling the body of POST
// /rule-itinerary/recalculate from the currently-shown result and the
// local slot/accommodation swap state (see slot-swaps.ts and
// accommodation-swap.ts). See the backend's
// RuleItineraryRecalculateRequest (PR #109, services/recalculate.py):
// fixed_slots must name every one of the trip's allowed
// (day_number, time_slot) slots exactly once - this module never decides
// which slots are allowed, it only mirrors whatever /generate's response
// already has one item per slot for (unchanged slots keep their original
// place_id, swapped slots use the swap's alternative place_id).
import { getActiveAlternativePlaceId, type SlotSwapMap } from "./slot-swaps";

export type RecalculateFixedSlot = {
  day_number: number;
  time_slot: string;
  place_id: string;
};

// Shape every call site actually needs - RuleItineraryItem satisfies this
// structurally, so the component never has to convert anything.
export type ItemForRecalculate = {
  day_number: number;
  time_slot: string;
  place_id?: string | null;
};

export type RecalculateAssembly =
  | { ok: true; fixed_slots: RecalculateFixedSlot[] }
  | { ok: false; reason: string };

// place_id가 없는 항목이 하나라도 있으면 조립 자체가 불가능하다 - 구버전
// 응답(캐시된 결과 등)은 normalizeGenerateResponse가 깨뜨리지 않고
// 통과시키므로, place_id 부재를 "항목이 비었다"가 아니라 "이 결과로는
// 재계산을 조립할 수 없다"는 별도 판정으로 다룬다.
export function buildFixedSlotsForRecalculate(items: ItemForRecalculate[], swaps: SlotSwapMap): RecalculateAssembly {
  const fixedSlots: RecalculateFixedSlot[] = [];
  for (const item of items) {
    const swappedPlaceId = getActiveAlternativePlaceId(swaps, item);
    const placeId = swappedPlaceId ?? item.place_id;
    if (!placeId) {
      return {
        ok: false,
        reason: "이 일정에는 재계산에 필요한 장소 정보가 없는 항목이 있어 다시 계산할 수 없어요.",
      };
    }
    fixedSlots.push({ day_number: item.day_number, time_slot: item.time_slot, place_id: placeId });
  }
  return { ok: true, fixed_slots: fixedSlots };
}

// "바뀐 일정으로 다시 계산" 버튼을 보여줄 수 있는지 - buildFixedSlotsForRecalculate
// 와 같은 기준(모든 항목에 place_id가 있어야 함)이지만 교체 상태와 무관하게
// (원본 place_id만 보고) 미리 판정할 수 있어 버튼 노출 여부에 그대로 쓴다.
export function canBuildFixedSlotsForRecalculate(items: ItemForRecalculate[]): boolean {
  return items.every((item) => typeof item.place_id === "string" && item.place_id.length > 0);
}

// /recalculate에 보낼 전체 요청 본문 - basePayload(마지막 /generate 호출 때
// 실제로 보낸 payload 그대로)를 베이스로 fixed_slots와(있을 때만)
// accommodation_id만 더한다. 폼의 "지금" 값으로 다시 조립하지 않는다 -
// 결과 화면에 온 뒤 폼 입력이 바뀌었을 수 있어서다(과제 constraint).
export function buildRecalculateRequestPayload(params: {
  basePayload: Record<string, unknown>;
  items: ItemForRecalculate[];
  slotSwaps: SlotSwapMap;
  accommodationId?: string | null;
}): { ok: true; payload: Record<string, unknown> } | { ok: false; reason: string } {
  const assembly = buildFixedSlotsForRecalculate(params.items, params.slotSwaps);
  if (!assembly.ok) {
    return assembly;
  }

  const payload: Record<string, unknown> = {
    ...params.basePayload,
    fixed_slots: assembly.fixed_slots,
  };
  if (params.accommodationId) {
    payload.accommodation_id = params.accommodationId;
  }
  return { ok: true, payload };
}
