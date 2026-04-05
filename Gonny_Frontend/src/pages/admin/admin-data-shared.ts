export type DestinationSummary = {
  continent: string;
  country: string;
  city: string;
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
  aliases: string[];
  default_days: number;
  places: PlaceData[];
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

export const continentLabels: Record<string, string> = {
  asia: "아시아",
  europe: "유럽",
};

export const countryLabels: Record<string, string> = {
  korea: "대한민국",
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
  { value: "food", label: "미식" },
  { value: "shopping", label: "쇼핑" },
  { value: "relax", label: "휴식" },
  { value: "nature", label: "자연" },
  { value: "photo", label: "사진" },
  { value: "activity", label: "액티비티" },
  { value: "local_experience", label: "현지 체험" },
  { value: "theme_park", label: "놀이공원" },
  { value: "family", label: "가족형" },
  { value: "nightlife", label: "야간" },
  { value: "cafe", label: "카페" },
];

export const timeOptions = [
  { value: "morning", label: "오전" },
  { value: "afternoon", label: "오후" },
  { value: "evening", label: "저녁" },
];

export const budgetOptions = [
  { value: "low", label: "가볍게" },
  { value: "medium", label: "중간" },
  { value: "high", label: "여유 있게" },
];

export const companionOptions = [
  { value: "solo", label: "혼자" },
  { value: "couple", label: "커플" },
  { value: "friend", label: "친구" },
  { value: "family", label: "가족" },
];

export const paceOptions = [
  { value: "easy", label: "여유롭게" },
  { value: "tight", label: "촘촘하게" },
];

export const mobilityOptions = [
  { value: "walkable", label: "도보 이동" },
  { value: "subway-friendly", label: "대중교통 편함" },
  { value: "train-friendly", label: "기차 이동 가능" },
  { value: "taxi-needed", label: "차량 이동 필요" },
  { value: "nearby", label: "가까운 거리" },
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

export function labelCategory(value: string) {
  return categoryOptions.find((option) => option.value === value)?.label ?? value;
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

export function toggleSelection(list: string[], value: string) {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
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

export function toPayload(state: PlaceEditorState): PlaceData {
  return {
    id: state.id.trim(),
    name: state.name.trim(),
    category: state.category,
    budget_level: state.budget_level,
    suitable_for: state.suitable_for,
    time_fit: state.time_fit,
    area: state.area.trim(),
    duration_hours: Number(state.duration_hours || 2),
    priority: Number(state.priority || 7),
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
    errors.push("장소명은 꼭 입력해 주세요.");
  }
  if (!editor.id.trim()) {
    errors.push("장소 아이디는 꼭 입력해 주세요.");
  }
  if (editor.id && !/^[a-z0-9-]+$/.test(editor.id.trim())) {
    errors.push("장소 아이디는 영문 소문자, 숫자, 하이픈(-)만 사용할 수 있어요.");
  }
  if (!editor.summary.trim()) {
    errors.push("소개 문장은 꼭 입력해 주세요.");
  }
  if (!editor.category.length) {
    errors.push("카테고리는 하나 이상 선택해 주세요.");
  }
  if (!editor.time_fit.length) {
    errors.push("시간대는 하나 이상 선택해 주세요.");
  }
  if (!editor.suitable_for.length) {
    errors.push("동행 유형은 하나 이상 선택해 주세요.");
  }
  if (!editor.budget_level.length) {
    errors.push("예산대는 하나 이상 선택해 주세요.");
  }
  if (Number.isNaN(Number(editor.priority)) || Number(editor.priority) < 1 || Number(editor.priority) > 20) {
    errors.push("추천 우선순위는 1부터 20 사이 숫자로 입력해 주세요.");
  }
  if (Number.isNaN(Number(editor.duration_hours)) || Number(editor.duration_hours) <= 0 || Number(editor.duration_hours) > 24) {
    errors.push("예상 소요 시간은 1부터 24 사이 숫자로 입력해 주세요.");
  }
  if (duplicateId) {
    errors.push("같은 도시에 같은 장소 아이디가 이미 있어요.");
  }
  if (duplicateName) {
    errors.push("같은 도시에 같은 장소명이 이미 있어요.");
  }
  if (isCreating && !catalog) {
    errors.push("도시 정보를 불러온 뒤 다시 시도해 주세요.");
  }

  return errors;
}
