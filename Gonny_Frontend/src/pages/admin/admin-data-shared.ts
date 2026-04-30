export type DestinationSummary = {
  continent: string;
  country: string;
  city: string;
  continent_label?: string | null;
  country_label?: string | null;
  city_label?: string | null;
  total_places: number;
  active_places: number;
  activity_places: number;
};

export type PlaceData = {
  id: string;
  name: string;
  category: string[];
  budget_level: string[];
  suitable_for: string[];
  time_fit: string[];
  area: string;
  duration_hours: number;
  priority: number;
  pace: string[];
  mobility: string[];
  summary: string;
  official_url?: string | null;
  booking_hint?: string | null;
  is_active?: boolean;
  mvp_tier?: string;
  full_day_recommended?: boolean;
  full_day_notes?: Record<string, string[]>;
  slot_bias?: Record<string, number>;
  mood_keywords?: string[];
  highlight_tags?: string[];
  note_templates?: string[];
};

export type CityCatalog = {
  continent: string;
  country: string;
  city: string;
  continent_label?: string | null;
  country_label?: string | null;
  city_label?: string | null;
  aliases: string[];
  default_days: number;
  places: PlaceData[];
};

export type DestinationEditorState = {
  continent: string;
  continent_label: string;
  country: string;
  country_label: string;
  city: string;
  city_label: string;
  aliases: string;
  default_days: string;
};

export type PlaceEditorState = {
  id: string;
  name: string;
  category: string[];
  budget_level: string[];
  suitable_for: string[];
  time_fit: string[];
  area: string;
  duration_hours: string;
  priority: string;
  pace: string[];
  mobility: string[];
  summary: string;
  official_url: string;
  booking_hint: string;
  is_active: boolean;
  mvp_tier: string;
  full_day_recommended: boolean;
  mood_keywords: string;
  highlight_tags: string;
  note_templates: string;
  slot_bias_morning: string;
  slot_bias_afternoon: string;
  slot_bias_evening: string;
  full_day_notes_morning: string;
  full_day_notes_afternoon: string;
  full_day_notes_evening: string;
};

export const PLACE_PRIORITY_MIN = 1;
export const PLACE_PRIORITY_MAX = 10;
export const PLACE_DURATION_MIN_HOURS = 1;
export const PLACE_DURATION_MAX_HOURS = 12;
export const DESTINATION_DEFAULT_DAYS_MIN = 1;
export const DESTINATION_DEFAULT_DAYS_MAX = 14;

export const defaultDayPresetOptions = [
  { value: "2", label: "2일" },
  { value: "3", label: "3일" },
  { value: "4", label: "4일" },
  { value: "5", label: "5일" },
  { value: "7", label: "7일" },
  { value: "10", label: "10일" },
];

export const durationPresetOptions = [
  { value: "1", label: "잠깐 들르기", description: "약 1시간" },
  { value: "2", label: "기본 코스", description: "약 2시간" },
  { value: "3", label: "여유 있게", description: "약 3시간" },
  { value: "4", label: "반나절", description: "약 4시간" },
  { value: "8", label: "하루 코스", description: "대표 액티비티 장소에 사용" },
];

export const slotWeightOptions = [
  { value: "0", label: "0" },
  { value: "1", label: "1" },
  { value: "2", label: "2" },
  { value: "3", label: "3" },
  { value: "5", label: "5" },
  { value: "8", label: "8" },
];

export const slotBiasPresetOptions = [
  { label: "오전 추천", description: "아침부터 방문하기 좋은 장소", morning: 8, afternoon: 2, evening: 0 },
  { label: "오후 추천", description: "오후에 가장 잘 어울리는 장소", morning: 1, afternoon: 8, evening: 1 },
  { label: "저녁 추천", description: "노을, 저녁 식사, 야간 일정에 어울림", morning: 0, afternoon: 2, evening: 8 },
  { label: "시간대 무관", description: "하루 어느 때든 넣기 쉬움", morning: 3, afternoon: 3, evening: 3 },
];

export const priorityPresetOptions = [
  { value: "3", label: "선택형", description: "넣으면 좋은 정도" },
  { value: "5", label: "추천", description: "무난하게 자주 추천" },
  { value: "7", label: "우선 추천", description: "비중 있게 자주 추천" },
  { value: "9", label: "대표 장소", description: "핵심 추천 장소" },
];

export const visibilityLevelOptions = [
  { value: "core", label: "대표 장소", description: "핵심 일정에 자주 노출됩니다." },
  { value: "standard", label: "일반 장소", description: "기본 추천 수준으로 노출됩니다." },
  { value: "hidden", label: "보조 장소", description: "조건이 잘 맞을 때만 드물게 노출됩니다." },
];

export const continentLabels: Record<string, string> = {
  asia: "아시아",
  europe: "유럽",
};

export const countryLabels: Record<string, string> = {
  korea: "한국",
  japan: "일본",
  thailand: "태국",
  taiwan: "대만",
  singapore: "싱가포르",
  france: "프랑스",
  italy: "이탈리아",
  spain: "스페인",
  russia: "러시아",
};

export const cityLabels: Record<string, string> = {
  seoul: "서울",
  busan: "부산",
  jeju: "제주",
  gangneung: "강릉",
  gyeongju: "경주",
  jeonju: "전주",
  sokcho: "속초",
  yeosu: "여수",
  tokyo: "도쿄",
  osaka: "오사카",
  kyoto: "교토",
  fukuoka: "후쿠오카",
  bangkok: "방콕",
  chiangmai: "치앙마이",
  taipei: "타이베이",
  singapore: "싱가포르",
  paris: "파리",
  rome: "로마",
  barcelona: "바르셀로나",
  vladivostok: "블라디보스토크",
};

export const categoryOptions = [
  { value: "sightseeing", label: "관광" },
  { value: "culture", label: "문화" },
  { value: "food", label: "맛집" },
  { value: "shopping", label: "쇼핑" },
  { value: "relax", label: "휴식" },
  { value: "nature", label: "자연" },
  { value: "photo", label: "사진 명소" },
  { value: "activity", label: "액티비티" },
  { value: "local_experience", label: "로컬 체험" },
  { value: "theme_park", label: "테마파크" },
  { value: "family", label: "가족 여행" },
  { value: "nightlife", label: "야간 명소" },
  { value: "cafe", label: "카페" },
];

export const timeOptions = [
  { value: "morning", label: "오전" },
  { value: "afternoon", label: "오후" },
  { value: "evening", label: "저녁" },
];

export const budgetOptions = [
  { value: "low", label: "가성비" },
  { value: "medium", label: "중간" },
  { value: "high", label: "프리미엄" },
];

export const companionOptions = [
  { value: "solo", label: "혼자" },
  { value: "couple", label: "커플" },
  { value: "friend", label: "친구" },
  { value: "family", label: "가족" },
];

export const paceOptions = [
  { value: "easy", label: "여유롭게" },
  { value: "tight", label: "빽빽하게" },
];

export const mobilityOptions = [
  { value: "walkable", label: "도보 이동" },
  { value: "subway-friendly", label: "지하철 이동" },
  { value: "train-friendly", label: "기차 이동" },
  { value: "taxi-needed", label: "택시 추천" },
  { value: "nearby", label: "가까운 동선" },
];

export function labelContinent(value: string) {
  return continentLabels[value] ?? value;
}

export function labelCountry(value: string) {
  return countryLabels[value] ?? value;
}

export function labelCity(value: string) {
  return cityLabels[value] ?? value;
}

export function displayContinent(destination: Pick<DestinationSummary, "continent" | "continent_label">) {
  return destination.continent_label?.trim() || labelContinent(destination.continent);
}

export function displayCountry(destination: Pick<DestinationSummary, "country" | "country_label">) {
  return destination.country_label?.trim() || labelCountry(destination.country);
}

export function displayCity(destination: Pick<DestinationSummary, "city" | "city_label">) {
  return destination.city_label?.trim() || labelCity(destination.city);
}

export function labelCategory(value: string) {
  return categoryOptions.find((option) => option.value === value)?.label ?? value;
}

export function labelVisibilityLevel(value: string) {
  return visibilityLevelOptions.find((option) => option.value === value)?.label ?? value;
}

export function labelBudgetBand(value: string) {
  return budgetOptions.find((option) => option.value === value)?.label ?? value;
}

export function joinList(value?: string[]) {
  return Array.isArray(value) ? value.join(", ") : "";
}

export function parseCommaList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function parseLineList(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function toPositiveInteger(value: string, fallback: number) {
  const parsed = Number.parseInt(value.trim(), 10);
  return Number.isNaN(parsed) ? fallback : parsed;
}

export function getApiErrorMessage(error: unknown, fallback: string) {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    typeof (error as { response?: unknown }).response === "object" &&
    (error as { response?: { data?: unknown } }).response?.data &&
    typeof (error as { response?: { data?: unknown } }).response?.data === "object"
  ) {
    const data = (error as { response?: { data?: { detail?: unknown } } }).response?.data;
    if (typeof data?.detail === "string" && data.detail.trim()) {
      return data.detail;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallback;
}

export function toggleSelection(list: string[], value: string) {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

export function applyDurationPreset(
  durationHours: string,
  presetValue: string,
): string {
  return durationHours === presetValue ? durationHours : presetValue;
}

export function applySlotBiasPreset(editor: PlaceEditorState, preset: { morning: number; afternoon: number; evening: number }) {
  return {
    ...editor,
    slot_bias_morning: String(preset.morning),
    slot_bias_afternoon: String(preset.afternoon),
    slot_bias_evening: String(preset.evening),
  };
}

export function toEditorState(place: PlaceData): PlaceEditorState {
  return {
    id: place.id,
    name: place.name,
    category: place.category,
    budget_level: place.budget_level,
    suitable_for: place.suitable_for,
    time_fit: place.time_fit,
    area: place.area,
    duration_hours: String(place.duration_hours),
    priority: String(place.priority),
    pace: place.pace,
    mobility: place.mobility,
    summary: place.summary,
    official_url: place.official_url ?? "",
    booking_hint: place.booking_hint ?? "",
    is_active: place.is_active ?? true,
    mvp_tier: place.mvp_tier ?? "standard",
    full_day_recommended: place.full_day_recommended ?? false,
    mood_keywords: joinList(place.mood_keywords),
    highlight_tags: joinList(place.highlight_tags),
    note_templates: joinList(place.note_templates),
    slot_bias_morning: String(place.slot_bias?.morning ?? 0),
    slot_bias_afternoon: String(place.slot_bias?.afternoon ?? 0),
    slot_bias_evening: String(place.slot_bias?.evening ?? 0),
    full_day_notes_morning: Array.isArray(place.full_day_notes?.morning) ? place.full_day_notes.morning.join("\n") : "",
    full_day_notes_afternoon: Array.isArray(place.full_day_notes?.afternoon)
      ? place.full_day_notes.afternoon.join("\n")
      : "",
    full_day_notes_evening: Array.isArray(place.full_day_notes?.evening) ? place.full_day_notes.evening.join("\n") : "",
  };
}

export function emptyEditorState(defaultArea = ""): PlaceEditorState {
  return {
    id: "",
    name: "",
    category: ["sightseeing"],
    budget_level: ["medium"],
    suitable_for: ["solo", "couple", "friend", "family"],
    time_fit: ["afternoon"],
    area: defaultArea,
    duration_hours: "2",
    priority: "7",
    pace: ["easy"],
    mobility: ["walkable"],
    summary: "",
    official_url: "",
    booking_hint: "",
    is_active: true,
    mvp_tier: "standard",
    full_day_recommended: false,
    mood_keywords: "",
    highlight_tags: "",
    note_templates: "",
    slot_bias_morning: "0",
    slot_bias_afternoon: "0",
    slot_bias_evening: "0",
    full_day_notes_morning: "",
    full_day_notes_afternoon: "",
    full_day_notes_evening: "",
  };
}

export function emptyDestinationEditorState(): DestinationEditorState {
  return {
    continent: "",
    continent_label: "",
    country: "",
    country_label: "",
    city: "",
    city_label: "",
    aliases: "",
    default_days: "3",
  };
}

export function toPayload(state: PlaceEditorState): PlaceData {
  return {
    id: state.id.trim(),
    name: state.name.trim(),
    category: state.category,
    budget_level: state.budget_level,
    suitable_for: state.suitable_for,
    time_fit: state.time_fit,
    area: state.area.trim(),
    duration_hours: toPositiveInteger(state.duration_hours, 2),
    priority: toPositiveInteger(state.priority, 7),
    pace: state.pace,
    mobility: state.mobility,
    summary: state.summary.trim(),
    official_url: state.official_url.trim() || null,
    booking_hint: state.booking_hint.trim() || null,
    is_active: state.is_active,
    mvp_tier: state.mvp_tier,
    full_day_recommended: state.full_day_recommended,
    full_day_notes: {
      morning: parseLineList(state.full_day_notes_morning),
      afternoon: parseLineList(state.full_day_notes_afternoon),
      evening: parseLineList(state.full_day_notes_evening),
    },
    slot_bias: {
      morning: Number(state.slot_bias_morning || 0),
      afternoon: Number(state.slot_bias_afternoon || 0),
      evening: Number(state.slot_bias_evening || 0),
    },
    mood_keywords: parseCommaList(state.mood_keywords),
    highlight_tags: parseCommaList(state.highlight_tags),
    note_templates: parseCommaList(state.note_templates),
  };
}

export function suggestPlaceId(city: string, name: string, existingIds: string[]) {
  const normalizedName = name
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, " ")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");

  const base = normalizedName ? `${city}-${normalizedName}` : `${city}-place`;
  if (!existingIds.includes(base)) {
    return base;
  }

  let index = existingIds.length + 1;
  let candidate = `${base}-${String(index).padStart(2, "0")}`;
  while (existingIds.includes(candidate)) {
    index += 1;
    candidate = `${base}-${String(index).padStart(2, "0")}`;
  }
  return candidate;
}

export function validatePlaceEditor(
  editor: PlaceEditorState,
  catalog: CityCatalog | null,
  isCreating: boolean,
  originalPlaceId: string,
) {
  const errors: string[] = [];
  const normalizedId = editor.id.trim().toLowerCase();
  const normalizedName = editor.name.trim().toLowerCase();
  const duplicateId = catalog?.places.some((place) => place.id.toLowerCase() === normalizedId && place.id !== originalPlaceId);
  const duplicateName = catalog?.places.some(
    (place) => place.name.trim().toLowerCase() === normalizedName && place.id !== originalPlaceId,
  );

  if (!editor.name.trim()) {
    errors.push("장소 이름을 입력해주세요.");
  }
  if (!editor.id.trim()) {
    errors.push("내부 식별용 영문 이름을 입력해주세요.");
  }
  if (editor.id && !/^[a-z0-9-]+$/.test(editor.id.trim())) {
    errors.push("내부 식별용 영문 이름은 영문 소문자, 숫자, 하이픈만 사용할 수 있습니다.");
  }
  if (!editor.area.trim()) {
    errors.push("지역 이름을 입력해주세요.");
  }
  if (!editor.summary.trim()) {
    errors.push("짧은 소개를 입력해주세요.");
  }
  if (!editor.category.length) {
    errors.push("카테고리를 하나 이상 선택해주세요.");
  }
  if (!editor.time_fit.length) {
    errors.push("추천 시간대를 하나 이상 선택해주세요.");
  }
  if (!editor.suitable_for.length) {
    errors.push("어울리는 여행 유형을 하나 이상 선택해주세요.");
  }
  if (!editor.budget_level.length) {
    errors.push("예산 구간을 하나 이상 선택해주세요.");
  }
  if (Number.isNaN(Number(editor.priority)) || Number(editor.priority) < PLACE_PRIORITY_MIN || Number(editor.priority) > PLACE_PRIORITY_MAX) {
    errors.push(`추천 우선순위는 ${PLACE_PRIORITY_MIN}부터 ${PLACE_PRIORITY_MAX} 사이여야 합니다.`);
  }
  if (
    Number.isNaN(Number(editor.duration_hours)) ||
    Number(editor.duration_hours) < PLACE_DURATION_MIN_HOURS ||
    Number(editor.duration_hours) > PLACE_DURATION_MAX_HOURS
  ) {
    errors.push(`예상 소요 시간은 ${PLACE_DURATION_MIN_HOURS}시간부터 ${PLACE_DURATION_MAX_HOURS}시간 사이여야 합니다.`);
  }
  if (duplicateId) {
    errors.push("같은 내부 식별용 영문 이름을 사용하는 장소가 이미 있습니다.");
  }
  if (duplicateName) {
    errors.push("같은 장소 이름을 사용하는 데이터가 이미 있습니다.");
  }
  if (isCreating && !catalog) {
    errors.push("여행지 데이터를 불러오는 중입니다. 잠시 후 다시 시도해주세요.");
  }

  return errors;
}

export function validateDestinationEditor(editor: DestinationEditorState, existingCities: string[]) {
  const errors: string[] = [];
  const continent = editor.continent.trim().toLowerCase();
  const country = editor.country.trim().toLowerCase();
  const city = editor.city.trim().toLowerCase();

  if (!continent) errors.push("대륙 영문 이름을 입력해주세요.");
  if (!editor.continent_label.trim()) errors.push("화면에 보여줄 대륙 이름을 입력해주세요.");
  if (!country) errors.push("국가 영문 이름을 입력해주세요.");
  if (!editor.country_label.trim()) errors.push("화면에 보여줄 국가 이름을 입력해주세요.");
  if (!city) errors.push("도시 영문 이름을 입력해주세요.");
  if (!editor.city_label.trim()) errors.push("화면에 보여줄 도시 이름을 입력해주세요.");

  if (continent && !/^[a-z0-9-]+$/.test(continent)) {
    errors.push("대륙 영문 이름은 영문 소문자, 숫자, 하이픈만 사용할 수 있습니다.");
  }
  if (country && !/^[a-z0-9-]+$/.test(country)) {
    errors.push("국가 영문 이름은 영문 소문자, 숫자, 하이픈만 사용할 수 있습니다.");
  }
  if (city && !/^[a-z0-9-]+$/.test(city)) {
    errors.push("도시 영문 이름은 영문 소문자, 숫자, 하이픈만 사용할 수 있습니다.");
  }
  if (existingCities.includes(city)) {
    errors.push("같은 도시 영문 이름이 이미 존재합니다.");
  }
  if (Number.isNaN(Number(editor.default_days)) || Number(editor.default_days) < 1 || Number(editor.default_days) > 14) {
    errors.push("기본 여행 일수는 1일부터 14일 사이여야 합니다.");
  }

  return errors;
}
