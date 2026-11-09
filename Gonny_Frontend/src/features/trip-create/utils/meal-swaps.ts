// Pure, React-free logic for the "다른 추천" meal-swap feature (see the
// trip-create-form result screen's meal cards). Kept separate from
// slot-swaps.ts (the activity-slot swap feature, PR #104/#109) - the two
// are independent concerns that happen to both feed the same "이동 시간
// 재계산 안 됨" presentation (see utils/timeline-hints.ts, which reads both),
// but neither module reads the other's state. Structurally mirrors
// slot-swaps.ts's own shape/functions one-to-one, same pattern
// weather-banner.tsx uses for its own local structural type copies -
// deliberately not importing from slot-swaps.ts to keep both modules
// independently reasoned about.
//
// A swap never touches the backend response itself (`result`). It's a
// purely client-side override: "for this (day_number, meal_type), show
// this alternative's fields instead of the original meal's."

export type MealAlternative = {
  place_id: string;
  place_name: string;
  category: string;
  area: string;
  notes: string;
  average_cost_krw?: number | null;
};

// Shape every call site actually needs - RuleMealRecommendation satisfies
// this structurally, so the component never has to convert anything.
export type SwappableMeal = {
  day_number: number;
  meal_type: string;
  // PR #118 - 구버전 응답(캐시 등)에는 없을 수 있어 옵셔널.
  place_id?: string | null;
  place_name: string;
  area: string;
  notes: string;
  travel_minutes_from_previous: number | null;
  hours_unverified?: boolean;
  reasons?: unknown[];
  alternatives?: MealAlternative[];
};

// Keyed by `${day_number}:${meal_type}` - unique within one itinerary
// response (a day has at most one breakfast/lunch/dinner each).
export type MealSwapMap = Record<string, MealAlternative>;

export function buildMealKey(dayNumber: number, mealType: string): string {
  return `${dayNumber}:${mealType}`;
}

function mealKeyForMeal(meal: Pick<SwappableMeal, "day_number" | "meal_type">): string {
  return buildMealKey(meal.day_number, meal.meal_type);
}

export function isMealSwapped(swaps: MealSwapMap, meal: Pick<SwappableMeal, "day_number" | "meal_type">): boolean {
  return mealKeyForMeal(meal) in swaps;
}

export function hasAnyMealSwap(swaps: MealSwapMap): boolean {
  return Object.keys(swaps).length > 0;
}

// 교체: 이 식사에 이 대안을 적용한다 (불변 - 새 맵을 반환한다).
export function applyMealSwap(
  swaps: MealSwapMap,
  meal: Pick<SwappableMeal, "day_number" | "meal_type">,
  alternative: MealAlternative,
): MealSwapMap {
  return { ...swaps, [mealKeyForMeal(meal)]: alternative };
}

// 되돌리기: 이 식사의 교체를 지운다 (없으면 같은 맵을 그대로 반환해 불필요한
// 리렌더를 피한다).
export function revertMealSwap(swaps: MealSwapMap, meal: Pick<SwappableMeal, "day_number" | "meal_type">): MealSwapMap {
  const key = mealKeyForMeal(meal);
  if (!(key in swaps)) {
    return swaps;
  }
  const next = { ...swaps };
  delete next[key];
  return next;
}

export function getActiveMealAlternativeId(
  swaps: MealSwapMap,
  meal: Pick<SwappableMeal, "day_number" | "meal_type">,
): string | null {
  return swaps[mealKeyForMeal(meal)]?.place_id ?? null;
}

// 저장·표시에 쓸 "현재 화면에 보여야 할" 값 - 교체 중이면 대안 값으로, 아니면
// 원래 값 그대로. place_id도 대안 값으로 바꿔 React key/식당 식별이 교체 후에도
// 안정적이게 한다. travel_minutes_from_previous는 교체 중이면 항상 null(원래
// 장소 기준 이동 시간이라 맞지 않음), reasons는 항상 빈 배열 - slot-swaps.ts의
// getEffectiveItem과 같은 계약. hours_unverified는 건드리지 않는다 - 이미
// meal_type 기준으로만 정해지는 값(아침이면 항상 true)이라 어느 식당으로
// 바뀌어도 그대로 유지하는 게 맞다(과제 constraint).
export function getEffectiveMeal<T extends SwappableMeal>(meal: T, swaps: MealSwapMap): T {
  const alternative = swaps[mealKeyForMeal(meal)];
  if (!alternative) {
    return meal;
  }
  return {
    ...meal,
    place_id: alternative.place_id,
    place_name: alternative.place_name,
    area: alternative.area,
    notes: alternative.notes,
    travel_minutes_from_previous: null,
    reasons: [],
  };
}

function effectivePlaceName(meal: SwappableMeal, swaps: MealSwapMap): string {
  return swaps[mealKeyForMeal(meal)]?.place_name ?? meal.place_name;
}

// candidateName이 currentMeal이 아닌 다른 식사에서, 또는 활동 슬롯(교체
// 반영된 이름)에서 이미 쓰이고 있는지 - 서버가 같은 장소를 다른 식사나
// 활동 슬롯에 지정하는 걸 422로 막으므로(PR #118), 프런트에서도 같은 이름을
// 미리 비활성화한다. activeEffectiveActivityPlaceNames는 호출부가
// slot-swaps.ts의 getEffectiveItem으로 이미 계산해 건네는 활동 쪽 이름
// 목록이다 - 이 모듈이 slot-swaps.ts를 직접 import하지 않기 위함.
export function isMealNameUsedElsewhere(
  allMeals: SwappableMeal[],
  mealSwaps: MealSwapMap,
  currentMeal: Pick<SwappableMeal, "day_number" | "meal_type">,
  candidateName: string,
  effectiveActivityPlaceNames: string[],
): boolean {
  const currentKey = mealKeyForMeal(currentMeal);
  const usedByAnotherMeal = allMeals.some((other) => {
    if (mealKeyForMeal(other) === currentKey) {
      return false;
    }
    return effectivePlaceName(other, mealSwaps) === candidateName;
  });
  if (usedByAnotherMeal) {
    return true;
  }
  return effectiveActivityPlaceNames.includes(candidateName);
}
