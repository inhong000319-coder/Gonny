import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../../../shared/api/client";
import { Button } from "../../../shared/components/ui/button";

type CatalogCityOption = {
  continent: string;
  country: string;
  city: string;
  aliases: string[];
};

type RuleItineraryCatalogResponse = {
  cities?: CatalogCityOption[];
};

type TimeSlot = "morning" | "afternoon" | "evening";
type BudgetBand = "low" | "medium" | "high";
type TripStyle = "tight" | "easy" | "near-stay" | "mobility-first";
type CompanionType = "solo" | "couple" | "friend" | "family";
type TripConcept = "food" | "shopping" | "relax" | "sightseeing" | "culture" | "nature";

type RuleItineraryItem = {
  day_number: number;
  time_slot: TimeSlot;
  place_name: string;
  category: string;
  area: string;
  notes: string;
};

type RuleItineraryResponse = {
  continent: string;
  country: string;
  city: string;
  travelers: number;
  nights: number;
  days: number;
  budget_band: BudgetBand;
  concepts: TripConcept[];
  style: TripStyle;
  companion_type: CompanionType;
  items: RuleItineraryItem[];
};

type PlannerFormState = {
  continent: string;
  country: string;
  city: string;
  travelers: number;
  duration_label: string;
  budget_value: string;
  budget_band: BudgetBand;
  concepts: TripConcept[];
  style: TripStyle;
  companion_type: CompanionType;
};

const STEP_COUNT = 4;
const conceptOptions: TripConcept[] = ["food", "shopping", "relax", "sightseeing", "culture", "nature"];
const budgetOptions: BudgetBand[] = ["low", "medium", "high"];
const styleOptions: TripStyle[] = ["tight", "easy", "near-stay", "mobility-first"];
const companionOptions: CompanionType[] = ["solo", "couple", "friend", "family"];
const travelerOptions = [
  { value: 1, label: "혼자 여행" },
  { value: 2, label: "둘이서 여행" },
  { value: 3, label: "셋이서 여행" },
  { value: 4, label: "넷이서 여행" },
  { value: 5, label: "5인 이상 여행" },
];
const nightsOptions = [1, 2, 3, 4, 5, 6];
const budgetStepOptions = [
  { value: 100000, label: "+10만원" },
  { value: 1000000, label: "+100만원" },
];

const initialForm: PlannerFormState = {
  continent: "",
  country: "",
  city: "",
  travelers: 2,
  duration_label: "2박 3일",
  budget_value: "",
  budget_band: "medium",
  concepts: ["sightseeing", "food"],
  style: "easy",
  companion_type: "friend",
};

const continentKo: Record<string, string> = {
  asia: "아시아",
  europe: "유럽",
};

const countryKo: Record<string, string> = {
  korea: "대한민국",
  japan: "일본",
  thailand: "태국",
  france: "프랑스",
  italy: "이탈리아",
  spain: "스페인",
  taiwan: "대만",
  singapore: "싱가포르",
  russia: "러시아",
};

const cityKo: Record<string, string> = {
  bangkok: "방콕",
  barcelona: "바르셀로나",
  busan: "부산",
  chiangmai: "치앙마이",
  fukuoka: "후쿠오카",
  gangneung: "강릉",
  gyeongju: "경주",
  jeju: "제주",
  jeonju: "전주",
  kyoto: "교토",
  osaka: "오사카",
  paris: "파리",
  rome: "로마",
  seoul: "서울",
  singapore: "싱가포르",
  sokcho: "속초",
  taipei: "타이베이",
  tokyo: "도쿄",
  vladivostok: "블라디보스토크",
  yeosu: "여수",
};

function toContinentLabel(value: string) {
  return continentKo[value] ?? value;
}

const continentStageLayout: Record<
  string,
  { left: string; top: string; width: string; height: string; theme: string; accent: string }
> = {
  asia: { left: "62%", top: "46%", width: "30%", height: "36%", theme: "theme-asia", accent: "도시 밀집" },
  europe: { left: "38%", top: "30%", width: "20%", height: "24%", theme: "theme-europe", accent: "감성 루트" },
};

function toCountryLabel(value: string) {
  return countryKo[value] ?? value;
}

function toCityLabel(value: string) {
  return cityKo[value] ?? value;
}

function labelConcept(value: TripConcept) {
  if (value === "food") return "미식";
  if (value === "shopping") return "쇼핑";
  if (value === "relax") return "휴양";
  if (value === "sightseeing") return "관광";
  if (value === "culture") return "문화";
  return "자연";
}

function labelBudget(value: BudgetBand) {
  if (value === "low") return "가볍게";
  if (value === "medium") return "균형 있게";
  return "조금 더 여유 있게";
}

function budgetRangeLabel(value: BudgetBand) {
  if (value === "low") return "예: 0원 ~ 100만원";
  if (value === "medium") return "예: 100만원 ~ 300만원";
  return "예: 300만원 이상";
}

function budgetHint(value: BudgetBand) {
  if (value === "low") return "가성비 좋은 동선으로 추천합니다.";
  if (value === "medium") return "비용과 만족도를 함께 챙깁니다.";
  return "조금 더 편안한 경험을 우선합니다.";
}

function labelStyle(value: TripStyle) {
  if (value === "tight") return "꽉 차게";
  if (value === "easy") return "여유 있게";
  if (value === "near-stay") return "숙소 근처 중심";
  return "이동 편의 우선";
}

function labelStyleDesc(value: TripStyle) {
  if (value === "tight") return "핵심 장소를 빠르게 많이 둘러봐요.";
  if (value === "easy") return "이동 부담을 줄이고 흐름을 부드럽게 잡아요.";
  if (value === "near-stay") return "한 지역에 머물며 편하게 즐겨요.";
  return "동선 효율과 접근성을 우선해요.";
}

function labelCompanion(value: CompanionType) {
  if (value === "solo") return "혼자";
  if (value === "couple") return "커플";
  if (value === "friend") return "친구";
  return "가족";
}

function labelCompanionDesc(value: CompanionType) {
  if (value === "solo") return "혼자 움직이기 부담 없는 일정";
  if (value === "couple") return "분위기와 여유를 살린 일정";
  if (value === "friend") return "함께 즐기기 좋은 활기 있는 일정";
  return "무리 없이 둘러보기 좋은 일정";
}

function labelTimeSlot(value: TimeSlot) {
  if (value === "morning") return "오전";
  if (value === "afternoon") return "오후";
  return "저녁";
}

function formatWon(value: number) {
  return `${value.toLocaleString("ko-KR")}원`;
}

function parseBudgetValue(value: string) {
  const parsed = Number(value);
  if (Number.isNaN(parsed) || parsed < 0) {
    return 0;
  }

  return parsed;
}

function buildDurationLabel(nights: number) {
  return `${nights}박 ${nights + 1}일`;
}

function parseNights(value: string) {
  const match = value.match(/(\d+)\s*박/);
  if (!match) {
    return 2;
  }

  return Number(match[1]);
}

function isCatalogCityOption(value: unknown): value is CatalogCityOption {
  if (!value || typeof value !== "object") {
    return false;
  }

  const option = value as Record<string, unknown>;
  return (
    typeof option.continent === "string" &&
    typeof option.country === "string" &&
    typeof option.city === "string" &&
    Array.isArray(option.aliases)
  );
}

function isRuleItineraryItem(value: unknown): value is RuleItineraryItem {
  if (!value || typeof value !== "object") {
    return false;
  }

  const item = value as Record<string, unknown>;
  return (
    typeof item.day_number === "number" &&
    typeof item.time_slot === "string" &&
    typeof item.place_name === "string" &&
    typeof item.category === "string" &&
    typeof item.area === "string" &&
    typeof item.notes === "string"
  );
}

function normalizeCatalogResponse(payload: unknown) {
  if (!payload || typeof payload !== "object") {
    return [];
  }

  const data = payload as RuleItineraryCatalogResponse;
  if (!Array.isArray(data.cities)) {
    return [];
  }

  return data.cities.filter(isCatalogCityOption);
}

function normalizeGenerateResponse(payload: unknown): RuleItineraryResponse {
  if (!payload || typeof payload !== "object") {
    throw new Error("일정 생성 응답 형식이 올바르지 않습니다.");
  }

  const data = payload as Partial<RuleItineraryResponse>;
  if (!Array.isArray(data.items)) {
    throw new Error("생성된 일정 항목이 없습니다.");
  }

  const items = data.items.filter(isRuleItineraryItem);
  if (items.length === 0) {
    throw new Error("생성된 일정 항목을 해석하지 못했습니다.");
  }

  return {
    continent: typeof data.continent === "string" ? data.continent : "",
    country: typeof data.country === "string" ? data.country : "",
    city: typeof data.city === "string" ? data.city : "",
    travelers: typeof data.travelers === "number" ? data.travelers : 0,
    nights: typeof data.nights === "number" ? data.nights : 0,
    days: typeof data.days === "number" ? data.days : 0,
    budget_band: (data.budget_band as BudgetBand) ?? "medium",
    concepts: Array.isArray(data.concepts) ? (data.concepts as TripConcept[]) : [],
    style: (data.style as TripStyle) ?? "easy",
    companion_type: (data.companion_type as CompanionType) ?? "friend",
    items,
  };
}

function groupByDay(items: RuleItineraryItem[]) {
  return items.reduce<Array<{ day: number; items: RuleItineraryItem[] }>>((groups, item) => {
    const current = groups.find((group) => group.day === item.day_number);
    if (current) {
      current.items.push(item);
      return groups;
    }

    groups.push({ day: item.day_number, items: [item] });
    return groups;
  }, []);
}

function countDistinctAreas(items: RuleItineraryItem[]) {
  return new Set(items.map((item) => item.area)).size;
}

function summarizeRoute(items: RuleItineraryItem[]) {
  if (items.length === 0) {
    return "";
  }

  const highlights = items.slice(0, 3).map((item) => item.place_name);
  return highlights.join(" · ");
}

export function TripCreateForm() {
  const [form, setForm] = useState<PlannerFormState>(initialForm);
  const [catalog, setCatalog] = useState<CatalogCityOption[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [currentStep, setCurrentStep] = useState(1);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<RuleItineraryResponse | null>(null);
  const hasResult = result !== null;

  useEffect(() => {
    async function loadCatalog() {
      setCatalogLoading(true);
      setError("");

      try {
        const response = await apiClient.get<unknown>("/rule-itinerary/options");
        const nextCatalog = normalizeCatalogResponse(response.data);
        setCatalog(nextCatalog);

        if (nextCatalog.length === 0) {
          setError("도시 목록을 아직 불러오지 못했습니다. 잠시 뒤 다시 시도해 주세요.");
        }
      } catch (loadError) {
        const nextError = loadError instanceof Error ? loadError.message : "도시 목록을 불러오지 못했습니다.";
        setCatalog([]);
        setError(nextError);
      } finally {
        setCatalogLoading(false);
      }
    }

    void loadCatalog();
  }, []);

  const continents = useMemo(
    () => [...new Set(catalog.map((option) => option.continent))].sort(),
    [catalog],
  );

  const countries = useMemo(() => {
    const filtered = catalog.filter((option) => !form.continent || option.continent === form.continent);
    return [...new Set(filtered.map((option) => option.country))].sort();
  }, [catalog, form.continent]);

  const cities = useMemo(
    () =>
      catalog
        .filter((option) => (!form.continent || option.continent === form.continent) && (!form.country || option.country === form.country))
        .sort((left, right) => toCityLabel(left.city).localeCompare(toCityLabel(right.city), "ko")),
    [catalog, form.continent, form.country],
  );

  const featuredCountries = useMemo(
    () =>
      countries.map((country) => {
        const sample = catalog.find((option) => option.country === country);
        return {
          key: country,
          label: toCountryLabel(country),
          continent: sample ? toContinentLabel(sample.continent) : "",
          cityCount: catalog.filter((option) => option.country === country).length,
        };
      }),
    [catalog, countries],
  );

  const mapContinents = useMemo(
    () =>
      continents.map((continent) => {
        const layout = continentStageLayout[continent] ?? {
          left: "50%",
          top: "50%",
          width: "24%",
          height: "24%",
          theme: "theme-generic",
          accent: "추천 도시",
        };

        return {
          key: continent,
          label: toContinentLabel(continent),
          countryCount: catalog.filter((option) => option.continent === continent).reduce((set, option) => set.add(option.country), new Set<string>())
            .size,
          cityCount: catalog.filter((option) => option.continent === continent).length,
          ...layout,
        };
      }),
    [catalog, continents],
  );

  const mapCountries = useMemo(
    () =>
      featuredCountries.map((country) => ({
        ...country,
        previewCities: catalog
          .filter((option) => option.country === country.key)
          .slice(0, 2)
          .map((option) => toCityLabel(option.city))
          .join(" · "),
      })),
    [catalog, featuredCountries],
  );

  const mapCities = useMemo(() => cities.slice(0, 8), [cities]);

  const groupedItems = useMemo(() => groupByDay(result?.items ?? []), [result]);
  const selectedBudgetValue = parseBudgetValue(form.budget_value);
  const selectedNights = parseNights(form.duration_label);
  const totalAreaCount = result ? countDistinctAreas(result.items) : 0;

  useEffect(() => {
    if (!form.city) {
      return;
    }

    const cityStillVisible = cities.some((option) => option.city === form.city);
    if (!cityStillVisible) {
      setForm((prev) => ({ ...prev, city: "" }));
    }
  }, [cities, form.city]);

  const updateField = <K extends keyof PlannerFormState>(key: K, value: PlannerFormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const toggleConcept = (concept: TripConcept) => {
    setForm((prev) => {
      const hasConcept = prev.concepts.includes(concept);
      const nextConcepts = hasConcept
        ? prev.concepts.filter((item) => item !== concept)
        : [...prev.concepts, concept];

      return {
        ...prev,
        concepts: nextConcepts.length > 0 ? nextConcepts : ["sightseeing"],
      };
    });
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError("");
    setMessage("");

    try {
      const response = await apiClient.post<unknown>("/rule-itinerary/generate", {
        ...form,
        budget_value: form.budget_value ? Number(form.budget_value) : null,
        travelers: Number(form.travelers) || 2,
      });

      const nextResult = normalizeGenerateResponse(response.data);
      setResult(nextResult);
      setCurrentStep(STEP_COUNT);
      setMessage(`${toCityLabel(nextResult.city)} 기준으로 ${nextResult.items.length}개의 일정이 생성되었습니다.`);
    } catch (generateError) {
      const nextError =
        generateError instanceof Error ? generateError.message : "규칙 기반 일정 생성에 실패했습니다.";
      setResult(null);
      setError(nextError);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleEditAgain = () => {
    setResult(null);
    setMessage("");
    setError("");
    setCurrentStep(STEP_COUNT);
  };

  const handleBudgetStep = (amount: number) => {
    const nextValue = Math.min(50000000, selectedBudgetValue + amount);
    updateField("budget_value", String(nextValue));
  };

  return (
    <div className={`page-grid ${hasResult ? "planner-result-layout" : "planner-form-layout"}`}>
      <section className="card card-tinted stack planner-card">
        {!hasResult ? (
          <>
            <div className="section-header">
              <div>
                <span className="section-kicker">Rule Planner</span>
                <h2 className="section-title">현재 화면에 맞춘 규칙 기반 일정 생성</h2>
                <p className="section-subtitle">
                  여행지, 기간, 예산, 분위기를 고르면 단계별로 확인한 뒤 일정을 생성할 수 있습니다.
                </p>
              </div>
              <div className="planner-api-badges">
                <span className="badge">도시 데이터 연동</span>
                <span className="badge">규칙 기반 추천</span>
              </div>
            </div>

            <div className="planner-step-row">
              {[1, 2, 3, 4].map((step) => (
                <button
                  key={step}
                  className={`planner-step-button ${currentStep === step ? "active" : ""} ${currentStep > step ? "done" : ""}`}
                  onClick={() => setCurrentStep(step)}
                  type="button"
                >
                  <span>{step}</span>
                  <strong>
                    {step === 1 && "여행지"}
                    {step === 2 && "기본 정보"}
                    {step === 3 && "여행 스타일"}
                    {step === 4 && "확인 및 생성"}
                  </strong>
                </button>
              ))}
            </div>

            {currentStep === 1 ? (
              <div className="stack">
                <div>
                  <h3 className="planner-stage-title">1. 여행지 선택</h3>
                  <p className="section-subtitle">
                    대륙을 고른 뒤, 마음이 가는 나라와 도시를 선택해 주세요. 카드로 먼저 둘러보면서 감을 잡아도 좋습니다.
                  </p>
                </div>

                <section className="planner-map-shell">
                  <div className="planner-map-copy">
                    <div>
                      <span className="section-kicker">Interactive Map</span>
                      <strong>지도로 먼저 감을 잡아보세요</strong>
                    </div>
                    <p>
                      대륙을 누르면 화면이 자연스럽게 집중되고, 이어서 국가와 도시까지 내려가는 흐름을 한 화면에서 함께
                      볼 수 있게 구성했습니다.
                    </p>
                  </div>

                  <div className={`planner-world-stage ${form.continent ? "is-focused" : ""}`}>
                    <div className="planner-world-grid" />
                    <div className="planner-world-orbit planner-world-orbit-one" />
                    <div className="planner-world-orbit planner-world-orbit-two" />
                    {mapContinents.map((continent) => (
                      <button
                        key={continent.key}
                        className={`planner-continent-node ${continent.theme} ${form.continent === continent.key ? "selected" : ""}`}
                        onClick={() => {
                          updateField("continent", continent.key);
                          updateField("country", "");
                          updateField("city", "");
                        }}
                        style={{
                          left: continent.left,
                          top: continent.top,
                          width: continent.width,
                          height: continent.height,
                        }}
                        type="button"
                      >
                        <strong>{continent.label}</strong>
                        <span>{continent.countryCount}개 국가</span>
                        <small>{continent.cityCount}개 도시 · {continent.accent}</small>
                      </button>
                    ))}
                    <div className="planner-map-focus">
                      <span>{form.continent ? `${toContinentLabel(form.continent)} 확대 보기` : "세계 지도 둘러보기"}</span>
                      <strong>
                        {form.city
                          ? `${toCityLabel(form.city)} 선택 완료`
                          : form.country
                            ? `${toCountryLabel(form.country)} 도시를 골라주세요`
                            : "대륙에서 시작해 국가와 도시까지 순서대로 내려가보세요"}
                      </strong>
                    </div>
                  </div>

                  <div className="planner-map-layers">
                    <article className="planner-map-panel">
                      <div className="planner-map-panel-head">
                        <span>1</span>
                        <strong>대륙</strong>
                      </div>
                      <div className="planner-map-chip-list">
                        {mapContinents.map((continent) => (
                          <button
                            key={continent.key}
                            className={`planner-map-chip ${form.continent === continent.key ? "selected" : ""}`}
                            onClick={() => {
                              updateField("continent", continent.key);
                              updateField("country", "");
                              updateField("city", "");
                            }}
                            type="button"
                          >
                            {continent.label}
                          </button>
                        ))}
                      </div>
                    </article>

                    <article className="planner-map-panel">
                      <div className="planner-map-panel-head">
                        <span>2</span>
                        <strong>국가</strong>
                      </div>
                      <div className="planner-map-country-list">
                        {mapCountries.map((country) => (
                          <button
                            key={country.key}
                            className={`planner-map-country-row ${form.country === country.key ? "selected" : ""}`}
                            onClick={() => {
                              updateField("country", country.key);
                              updateField("city", "");
                            }}
                            type="button"
                          >
                            <div>
                              <strong>{country.label}</strong>
                              <span>{country.continent}</span>
                            </div>
                            <small>{country.previewCities || "도시 준비 중"}</small>
                          </button>
                        ))}
                      </div>
                    </article>

                    <article className="planner-map-panel">
                      <div className="planner-map-panel-head">
                        <span>3</span>
                        <strong>도시</strong>
                      </div>
                      <div className="planner-map-city-list">
                        {mapCities.map((option) => (
                          <button
                            key={`${option.country}-${option.city}-map`}
                            className={`planner-map-city-pill ${form.city === option.city ? "selected" : ""}`}
                            onClick={() => {
                              updateField("continent", option.continent);
                              updateField("country", option.country);
                              updateField("city", option.city);
                            }}
                            type="button"
                          >
                            <strong>{toCityLabel(option.city)}</strong>
                            <span>{toCountryLabel(option.country)}</span>
                          </button>
                        ))}
                      </div>
                    </article>
                  </div>
                </section>

                <div className="planner-form-grid">
                  <label className="field">
                    <span>대륙</span>
                    <select
                      onChange={(event) => {
                        updateField("continent", event.target.value);
                        updateField("country", "");
                        updateField("city", "");
                      }}
                      value={form.continent}
                    >
                      <option value="">전체 대륙</option>
                      {continents.map((continent) => (
                        <option key={continent} value={continent}>
                          {toContinentLabel(continent)}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="field">
                    <span>국가</span>
                    <select
                      onChange={(event) => {
                        updateField("country", event.target.value);
                        updateField("city", "");
                      }}
                      value={form.country}
                    >
                      <option value="">전체 국가</option>
                      {countries.map((country) => (
                        <option key={country} value={country}>
                          {toCountryLabel(country)}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="field planner-field-wide">
                    <span>도시</span>
                    <select onChange={(event) => updateField("city", event.target.value)} value={form.city}>
                      <option value="">자동 선택</option>
                      {cities.map((option) => (
                        <option key={`${option.country}-${option.city}`} value={option.city}>
                          {toCityLabel(option.city)}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="planner-country-section">
                  <div className="planner-country-heading">
                    <strong>나라부터 골라볼까요?</strong>
                    <span>{form.continent ? `${toContinentLabel(form.continent)} 안에서 선택 중` : "전체 국가 보기"}</span>
                  </div>
                  <div className="planner-country-grid">
                    {featuredCountries.map((country) => (
                      <button
                        key={country.key}
                        className={`planner-country-card ${form.country === country.key ? "selected" : ""}`}
                        onClick={() => {
                          updateField("country", country.key);
                          updateField("city", "");
                        }}
                        type="button"
                      >
                        <strong>{country.label}</strong>
                        <span>{country.continent}</span>
                        <small>{country.cityCount}개 도시</small>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="planner-city-grid">
                  {cities.map((option) => (
                    <button
                      key={`${option.country}-${option.city}`}
                      className={`planner-city-card ${form.city === option.city ? "selected" : ""}`}
                      onClick={() => {
                        updateField("continent", option.continent);
                        updateField("country", option.country);
                        updateField("city", option.city);
                      }}
                      type="button"
                    >
                      <strong>{toCityLabel(option.city)}</strong>
                      <span>{toCountryLabel(option.country)}</span>
                      <small>{toContinentLabel(option.continent)}</small>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {currentStep === 2 ? (
              <div className="stack">
                <div>
                  <h3 className="planner-stage-title">2. 기본 여행 정보</h3>
                  <p className="section-subtitle">기간과 인원, 예산 톤을 정하면 일정 밀도가 더 자연스럽게 맞춰집니다.</p>
                </div>

                <div className="planner-input-panel">
                  <div className="field">
                    <span>여행 인원</span>
                    <div className="planner-chip-grid planner-chip-grid-travelers">
                      {travelerOptions.map((option) => (
                        <button
                          key={option.value}
                          className={`planner-select-chip ${form.travelers === option.value ? "selected" : ""}`}
                          onClick={() => updateField("travelers", option.value)}
                          type="button"
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="field">
                    <span>여행 기간</span>
                    <div className="planner-chip-grid planner-chip-grid-nights">
                      {nightsOptions.map((night) => (
                        <button
                          key={night}
                          className={`planner-select-chip ${selectedNights === night ? "selected" : ""}`}
                          onClick={() => updateField("duration_label", buildDurationLabel(night))}
                          type="button"
                        >
                          {night}박
                        </button>
                      ))}
                    </div>
                    <p className="planner-inline-note">현재 선택: {form.duration_label}</p>
                  </div>

                  <div className="field">
                    <span>예산 설정</span>
                    <div className="planner-budget-shell">
                      <div className="planner-budget-display">
                        <strong>{formatWon(selectedBudgetValue)}</strong>
                        <span>버튼으로 빠르게 올리거나 슬라이더로 세밀하게 조정하세요.</span>
                      </div>
                      <div className="planner-budget-actions">
                        {budgetStepOptions.map((option) => (
                          <button
                            key={option.value}
                            className="planner-budget-step"
                            onClick={() => handleBudgetStep(option.value)}
                            type="button"
                          >
                            {option.label}
                          </button>
                        ))}
                        <button
                          className="planner-budget-step planner-budget-reset"
                          onClick={() => updateField("budget_value", "0")}
                          type="button"
                        >
                          초기화
                        </button>
                      </div>
                      <label className="planner-slider-wrap">
                        <span>예산 구간 슬라이더</span>
                        <input
                          max="50000000"
                          min="0"
                          onChange={(event) => updateField("budget_value", event.target.value)}
                          step="100000"
                          type="range"
                          value={selectedBudgetValue}
                        />
                        <div className="planner-slider-labels">
                          <span>0원</span>
                          <span>5천만원</span>
                        </div>
                      </label>
                    </div>
                  </div>
                </div>

                <div className="planner-choice-grid">
                  {budgetOptions.map((option) => (
                    <button
                      key={option}
                      className={`planner-choice-card ${form.budget_band === option ? "selected" : ""}`}
                      onClick={() => updateField("budget_band", option)}
                      type="button"
                    >
                      <strong>{labelBudget(option)}</strong>
                      <small>{budgetRangeLabel(option)}</small>
                      <span>{budgetHint(option)}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {currentStep === 3 ? (
              <div className="stack">
                <div>
                  <h3 className="planner-stage-title">3. 여행 스타일 설정</h3>
                  <p className="section-subtitle">원하는 분위기와 동행 유형에 맞춰 추천 기준을 바꿉니다.</p>
                </div>

                <div className="field">
                  <span>관심 테마</span>
                  <div className="chip-list">
                    {conceptOptions.map((concept) => (
                      <button
                        key={concept}
                        className={form.concepts.includes(concept) ? "chip active" : "chip"}
                        onClick={() => toggleConcept(concept)}
                        type="button"
                      >
                        {labelConcept(concept)}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="planner-section-block">
                  <div className="planner-section-copy">
                    <strong>일정 운영 방식</strong>
                    <span>동선을 얼마나 촘촘하게 짤지, 이동을 어떻게 다룰지 정합니다.</span>
                  </div>
                  <div className="planner-choice-grid">
                    {styleOptions.map((option) => (
                      <button
                        key={option}
                        className={`planner-choice-card ${form.style === option ? "selected" : ""}`}
                        onClick={() => updateField("style", option)}
                        type="button"
                      >
                        <strong>{labelStyle(option)}</strong>
                        <span>{labelStyleDesc(option)}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="planner-section-block">
                  <div className="planner-section-copy">
                    <strong>누구와 함께 가나요?</strong>
                    <span>같은 도시라도 동행 유형에 따라 추천 장소와 페이스가 달라집니다.</span>
                  </div>
                  <div className="planner-choice-grid">
                    {companionOptions.map((option) => (
                      <button
                        key={option}
                        className={`planner-choice-card ${form.companion_type === option ? "selected" : ""}`}
                        onClick={() => updateField("companion_type", option)}
                        type="button"
                      >
                        <strong>{labelCompanion(option)}</strong>
                        <span>{labelCompanionDesc(option)}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}

            {currentStep === 4 ? (
              <div className="stack">
                <div>
                  <h3 className="planner-stage-title">4. 확인 후 일정 생성</h3>
                  <p className="section-subtitle">입력한 조건을 마지막으로 확인하고 바로 생성할 수 있습니다.</p>
                </div>

                <div className="planner-review-grid">
                  <article className="metric">
                    <strong>여행지</strong>
                    <p>{form.city ? toCityLabel(form.city) : "자동 선택"}</p>
                    <span>
                      {form.country ? toCountryLabel(form.country) : "전체 국가"} · {form.continent ? toContinentLabel(form.continent) : "전체 대륙"}
                    </span>
                  </article>

                  <article className="metric">
                    <strong>기간과 인원</strong>
                    <p>
                      {form.duration_label || "2박 3일"} · {form.travelers === 5 ? "5인 이상" : `${form.travelers}명`}
                    </p>
                    <span>일정 길이에 맞춰 day 단위로 나눠 생성합니다.</span>
                  </article>

                  <article className="metric">
                    <strong>예산</strong>
                    <p>{labelBudget(form.budget_band)}</p>
                    <span>{formatWon(selectedBudgetValue)} 기준으로 보정합니다.</span>
                  </article>

                  <article className="metric">
                    <strong>스타일</strong>
                    <p>{labelStyle(form.style)}</p>
                    <span>{form.concepts.map(labelConcept).join(", ")}</span>
                  </article>
                </div>

                <div className="row">
                  <Button disabled={isGenerating} onClick={handleGenerate} type="button">
                    {isGenerating ? "일정 생성 중..." : "규칙 기반 일정 생성"}
                  </Button>
                </div>
              </div>
            ) : null}

            <div className="row">
              <Button
                disabled={currentStep === 1}
                onClick={() => setCurrentStep((step) => Math.max(1, step - 1))}
                type="button"
                variant="secondary"
              >
                이전
              </Button>
              <Button
                disabled={currentStep === STEP_COUNT}
                onClick={() => setCurrentStep((step) => Math.min(STEP_COUNT, step + 1))}
                type="button"
                variant="ghost"
              >
                다음
              </Button>
            </div>

            <div className="planner-status-grid">
              <div className="metric">
                <strong>도시 카탈로그</strong>
                <p>{catalogLoading ? "불러오는 중..." : `${catalog.length}개 도시`}</p>
                <span>백엔드 JSON 데이터셋과 연결되어 있습니다.</span>
              </div>
              <div className="metric">
                <strong>현재 기준 도시</strong>
                <p>{form.city ? toCityLabel(form.city) : "자동 선택"}</p>
                <span>선택이 없으면 시스템이 기본 도시를 자동으로 잡습니다.</span>
              </div>
            </div>

            {message ? <p className="planner-feedback success">{message}</p> : null}
            {error ? <p className="planner-feedback error">{error}</p> : null}
          </>
        ) : (
          <>
            <div className="planner-result-hero">
              <div className="planner-result-copy">
                <span className="section-kicker">Generated Itinerary</span>
                <h2 className="planner-result-title">{toCityLabel(result.city)} 일정이 준비됐어요</h2>
                <p className="planner-result-description">
                  {toCountryLabel(result.country)}에서 {result.nights}박 {result.days}일 동안 {labelStyle(result.style)} 흐름으로 즐길 수 있게 정리했습니다.
                </p>
                <div className="planner-result-tags">
                  <span className="badge">{labelCompanion(result.companion_type)}</span>
                  <span className="badge">{labelBudget(result.budget_band)}</span>
                  {result.concepts.map((concept) => (
                    <span key={concept} className="badge">
                      {labelConcept(concept)}
                    </span>
                  ))}
                </div>
              </div>
              <div className="planner-result-glance">
                <div className="planner-glance-card">
                  <span>추천 장소</span>
                  <strong>{result.items.length}곳</strong>
                </div>
                <div className="planner-glance-card">
                  <span>이동 권역</span>
                  <strong>{totalAreaCount}개</strong>
                </div>
                <div className="planner-glance-card">
                  <span>대표 코스</span>
                  <strong>{summarizeRoute(result.items)}</strong>
                </div>
              </div>
            </div>

            <div className="planner-result-summary">
              <article className="metric">
                <strong>여행지</strong>
                <p>{toCityLabel(result.city)}</p>
                <span>
                  {toCountryLabel(result.country)} · {toContinentLabel(result.continent)}
                </span>
              </article>
              <article className="metric">
                <strong>기간과 인원</strong>
                <p>
                  {result.nights}박 {result.days}일 · {result.travelers}명
                </p>
                <span>{labelStyle(result.style)} 기준으로 정리되었습니다.</span>
              </article>
              <article className="metric">
                <strong>예산</strong>
                <p>{labelBudget(result.budget_band)}</p>
                <span>{result.concepts.map(labelConcept).join(", ")}</span>
              </article>
              <article className="metric">
                <strong>동행 유형</strong>
                <p>{labelCompanion(result.companion_type)}</p>
                <span>현재 기준에 맞게 동선을 배치했습니다.</span>
              </article>
            </div>

            {message ? <p className="planner-feedback success">{message}</p> : null}
            {error ? <p className="planner-feedback error">{error}</p> : null}

            <div className="planner-days-shell">
              <div className="planner-days-header">
                <div>
                  <strong>일차별 추천 동선</strong>
                  <span>오전, 오후, 저녁 흐름으로 끊어서 보기 쉽게 정리했습니다.</span>
                </div>
              </div>
              {groupedItems.map((group) => (
                <article key={group.day} className="planner-day-card">
                  <div className="planner-day-header">
                    <div>
                      <span className="planner-day-label">DAY {group.day}</span>
                      <strong className="trip-card-title">{group.day}일차</strong>
                    </div>
                    <p>{summarizeRoute(group.items)}</p>
                  </div>
                  <div className="planner-day-timeline">
                    {group.items.map((item) => (
                      <article key={`${group.day}-${item.time_slot}-${item.place_name}`} className="planner-stop-card">
                        <div className="planner-stop-time">
                          <span>{labelTimeSlot(item.time_slot)}</span>
                        </div>
                        <div className="planner-stop-body">
                          <div className="planner-slot-top">
                            <strong>{item.place_name}</strong>
                            <span className="badge">{item.category}</span>
                          </div>
                          <p className="planner-slot-area">{item.area}</p>
                          <p className="planner-slot-note">{item.notes}</p>
                        </div>
                      </article>
                    ))}
                  </div>
                </article>
              ))}
            </div>

            <div className="planner-result-actions">
              <Button onClick={handleEditAgain} type="button" variant="secondary">
                조건 다시 수정하기
              </Button>
              <Button onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })} type="button" variant="ghost">
                상단으로 이동
              </Button>
            </div>

            <details className="planner-raw-panel">
              <summary>원본 JSON 보기</summary>
              <pre>{JSON.stringify(result, null, 2)}</pre>
            </details>
          </>
        )}
      </section>
    </div>
  );
}
