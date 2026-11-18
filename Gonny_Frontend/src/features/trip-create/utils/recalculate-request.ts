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
import { getActiveMealAlternativeId, type MealSwapMap, type SwappableMeal } from "./meal-swaps";

export type RecalculateFixedSlot = {
  day_number: number;
  time_slot: string;
  place_id: string;
};

export type RecalculateFixedMeal = {
  day_number: number;
  meal_type: string;
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

// mealSwaps에 있는 식사만(사용자가 직접 고른 것만) fixed_meals로 보낸다 -
// 고르지 않은 식사는 서버가 다시 뽑게 둔다(과제 constraint). 활동
// fixed_slots와 달리 "전부 지정해야 함" 규칙이 없으므로 place_id가 없어
// 조립이 막히는 경우도 없다(대안을 고른 식사만 들어오고, 대안은 항상
// place_id를 갖는다).
export function buildFixedMealsForRecalculate(
  meals: SwappableMeal[],
  mealSwaps: MealSwapMap,
): RecalculateFixedMeal[] {
  const fixedMeals: RecalculateFixedMeal[] = [];
  for (const meal of meals) {
    const swappedPlaceId = getActiveMealAlternativeId(mealSwaps, meal);
    if (swappedPlaceId) {
      fixedMeals.push({ day_number: meal.day_number, meal_type: meal.meal_type, place_id: swappedPlaceId });
    }
  }
  return fixedMeals;
}

// 분할된(stay가 2곳 이상인) 일정을 재계산할 때 쓸, stay별 "밤 수 +
// 보낼 숙소 id" - stay_index 순서 그대로. accommodationId는 그 stay를
// 교체했으면 교체된 숙소 id, 아니면(기본 선택 유지) 원래 그 stay의 숙소
// id - 백엔드는 null을 "그 자리는 기본 선택"으로 해석하지만, 여기서는
// 항상 "현재 화면에 보이는 숙소"를 그대로 고정해 보낸다(재계산 전후로
// 화면에 보이는 숙소가 바뀌지 않게).
export type AccommodationStayForRecalculate = {
  nights: number;
  accommodationId: string | null;
};

// /recalculate에 보낼 전체 요청 본문 - basePayload(마지막 /generate 호출 때
// 실제로 보낸 payload 그대로)를 베이스로 fixed_slots와(있을 때만)
// accommodation_id 또는 stay_nights/stay_accommodation_ids, fixed_meals만
// 더한다. 폼의 "지금" 값으로 다시 조립하지 않는다 - 결과 화면에 온 뒤 폼
// 입력이 바뀌었을 수 있어서다(과제 constraint). meals/mealSwaps/
// accommodationStays는 선택 파라미터 - 기존 호출부(활동/숙소 교체만
// 다루던 호출)는 그대로 동작한다.
//
// accommodationStays가 있고 길이가 2 이상이면(#133 분할 일정) 그 분할
// 그대로 stay_nights/stay_accommodation_ids를 보내고, accommodationId는
// 무시한다(백엔드가 둘을 동시에 받으면 거부하므로 - 분할 일정에서는
// accommodation_id를 보내지 않는다). stay가 1곳 이하면(기본 경로)
// accommodationId만 쓰는 기존 동작과 완전히 같다.
export function buildRecalculateRequestPayload(params: {
  basePayload: Record<string, unknown>;
  items: ItemForRecalculate[];
  slotSwaps: SlotSwapMap;
  accommodationId?: string | null;
  accommodationStays?: AccommodationStayForRecalculate[];
  meals?: SwappableMeal[];
  mealSwaps?: MealSwapMap;
}): { ok: true; payload: Record<string, unknown> } | { ok: false; reason: string } {
  const assembly = buildFixedSlotsForRecalculate(params.items, params.slotSwaps);
  if (!assembly.ok) {
    return assembly;
  }

  const payload: Record<string, unknown> = {
    ...params.basePayload,
    fixed_slots: assembly.fixed_slots,
  };
  if (params.accommodationStays && params.accommodationStays.length >= 2) {
    payload.stay_nights = params.accommodationStays.map((stay) => stay.nights);
    payload.stay_accommodation_ids = params.accommodationStays.map((stay) => stay.accommodationId);
  } else if (params.accommodationId) {
    payload.accommodation_id = params.accommodationId;
  }
  if (params.meals && params.mealSwaps) {
    const fixedMeals = buildFixedMealsForRecalculate(params.meals, params.mealSwaps);
    if (fixedMeals.length > 0) {
      payload.fixed_meals = fixedMeals;
    }
  }
  return { ok: true, payload };
}
