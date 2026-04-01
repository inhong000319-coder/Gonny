import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../../api/client";

const TEXT = {
  plannerKicker: "\ub2e8\uacc4\ud615 \ud50c\ub798\ub108",
  plannerTitle: "\uaddc\uce59\uae30\ubc18 \uc5ec\ud589 \ub9cc\ub4e4\uae30",
  step1: "\uc5ec\ud589\uc9c0 \uc120\ud0dd",
  step2: "\uae30\ubcf8 \uc124\uc815",
  step3: "\uc2a4\ud0c0\uc77c \uc124\uc815",
  step4: "\uacb0\uacfc \ud655\uc778",
  step1Title: "1\ub2e8\uacc4. \uc5ec\ud589\uc9c0 \uc120\ud0dd",
  step1Desc:
    "\ub300\ub959, \uad6d\uac00, \ub3c4\uc2dc\ub97c \uc21c\uc11c\ub300\ub85c \uace0\ub974\uc138\uc694. \uc77c\ubd80 \ud56d\ubaa9\uc740 \uac74\ub108\ub6f0\uc5b4\ub3c4 \uc77c\uc815 \uc0dd\uc131\uc774 \uac00\ub2a5\ud569\ub2c8\ub2e4.",
  step2Title: "2\ub2e8\uacc4. \uae30\ubcf8 \uc5ec\ud589 \uc815\ubcf4",
  step2Desc:
    "\uc5ec\ud589 \uae30\uac04, \uc778\uc6d0 \uc218, \uc608\uc0b0\uc744 \uc815\ud558\uc138\uc694. \ube44\uc5b4 \uc788\ub294 \uac12\uc740 \uae30\ubcf8 \uaddc\uce59\uc73c\ub85c \ubcf4\uc815\ub429\ub2c8\ub2e4.",
  step3Title: "3\ub2e8\uacc4. \uc5ec\ud589 \ubd84\uc704\uae30 \uc124\uc815",
  step3Desc:
    "\uc5ec\ud589 \ucee8\uc149, \uc5ec\ud589 \uc2a4\ud0c0\uc77c, \ub3d9\ud589 \uc720\ud615\uc744 \uc120\ud0dd\ud574 \uc77c\uc815 \ubd84\uc704\uae30\ub97c \uc815\ud558\uc138\uc694.",
  step4Title: "4\ub2e8\uacc4. \uacb0\uacfc \ud655\uc778 \ubc0f \uc0dd\uc131",
  step4Desc: "\ucd5c\uc885 \uc785\ub825\uac12\uc744 \ud655\uc778\ud55c \ub4a4 \uaddc\uce59\uae30\ubc18 \uc77c\uc815\uc744 \uc0dd\uc131\ud558\uc138\uc694.",
  continent: "\ub300\ub959",
  country: "\uad6d\uac00",
  city: "\ub3c4\uc2dc",
  anyContinent: "\uc804\uccb4 \ub300\ub959",
  anyCountry: "\uc804\uccb4 \uad6d\uac00",
  travelers: "\uc5ec\ud589 \uc778\uc6d0",
  duration: "\uc5ec\ud589 \uae30\uac04",
  budgetValue: "\uc608\uc0b0 \uc9c1\uc811 \uc785\ub825",
  optional: "\uc120\ud0dd \uc785\ub825",
  concepts: "\uc5ec\ud589 \ucee8\uc149",
  previous: "\uc774\uc804",
  next: "\ub2e4\uc74c",
  catalog: "\ub3c4\uc2dc \uce74\ud0c8\ub85c\uadf8",
  currentCity: "\ud604\uc7ac \ub3c4\uc2dc",
  loadingCities: "\ubd88\ub7ec\uc624\ub294 \uc911",
  notSelected: "\uc120\ud0dd \uc548 \ub428",
  resultKicker: "\uc0dd\uc131\ub41c \uc77c\uc815",
  resultTitle: "\uc0dd\uc131 \uacb0\uacfc",
  emptyTitle: "\uc544\uc9c1 \uc0dd\uc131\ub41c \uc77c\uc815\uc774 \uc5c6\uc2b5\ub2c8\ub2e4",
  emptyDesc: "\ub2e8\uacc4\ub97c \uc21c\uc11c\ub300\ub85c \uc9c4\ud589\ud55c \ub4a4 \uc77c\uc815\uc744 \uc0dd\uc131\ud558\uba74 \uc774\uacf3\uc5d0 \uacb0\uacfc\uac00 \ud45c\uc2dc\ub429\ub2c8\ub2e4.",
  rawJson: "\uc6d0\ubcf8 \u004a\u0053\u004f\u004e \ubcf4\uae30",
  generate: "\uaddc\uce59\uae30\ubc18 \uc77c\uc815 \uc0dd\uc131",
  generating: "\uc0dd\uc131 \uc911...",
  autoSelect: "\uc790\ub3d9 \uc120\ud0dd",
  noDirectBudget: "\uc9c1\uc811 \uc785\ub825 \uc5c6\uc74c",
  enteredBudgetPrefix: "\uc785\ub825\uac12",
};

const initialForm = {
  continent: "",
  country: "",
  city: "vladivostok",
  travelers: 2,
  duration_label: "\u0032\ubc153\uc77c",
  budget_value: "",
  budget_band: "low",
  concepts: ["sightseeing", "food"],
  style: "easy",
  companion_type: "friend",
};

const STEP_COUNT = 4;
const conceptOptions = ["food", "shopping", "relax", "sightseeing", "culture", "nature"];
const budgetOptions = ["low", "medium", "high"];
const styleOptions = ["tight", "easy", "near-stay", "mobility-first"];
const companionOptions = ["solo", "couple", "friend", "family"];

function labelConcept(value) {
  if (value === "food") return "\uc2dd\uc0ac";
  if (value === "shopping") return "\uc1fc\ud551";
  if (value === "relax") return "\ud734\uc591";
  if (value === "sightseeing") return "\uad00\uad11";
  if (value === "culture") return "\ubb38\ud654";
  return "\uc790\uc5f0";
}

function labelBudget(value) {
  if (value === "low") return "\uc800\uc608\uc0b0";
  if (value === "medium") return "\uc911\uac04 \uc608\uc0b0";
  return "\uace0\uc608\uc0b0";
}

function labelStyle(value) {
  if (value === "tight") return "\ud0c0\uc774\ud2b8";
  if (value === "easy") return "\ub110\ub110";
  if (value === "near-stay") return "\uc219\uc18c \uadfc\ucc98 \uc704\uc8fc";
  return "\uc774\ub3d9 \ud3b8\ud568 \uc6b0\uc120";
}

function labelStyleDesc(value) {
  if (value === "tight") return "\ub354 \ucd18\ucd18\ud55c \uc77c\uc815";
  if (value === "easy") return "\uc5ec\uc720 \uc788\ub294 \ub3d9\uc120";
  if (value === "near-stay") return "\ud55c \uc9c0\uc5ed \uc911\uc2ec \uc774\ub3d9";
  return "\uc774\ub3d9 \ubd80\ub2f4 \uc904\uc774\uae30";
}

function labelCompanion(value) {
  if (value === "solo") return "\ud63c\uc790";
  if (value === "couple") return "\ucee4\ud50c";
  if (value === "friend") return "\uce5c\uad6c";
  return "\uac00\uc871";
}

function labelCompanionDesc(value) {
  if (value === "solo") return "\uc790\uc720\ub86d\uace0 \ub3c5\ub9bd\uc801\uc778 \uc77c\uc815";
  if (value === "couple") return "\uac10\uc131 \uc788\uace0 \ucc28\ubd84\ud55c \ubd84\uc704\uae30";
  if (value === "friend") return "\ud568\uaed8 \uc990\uae30\uae30 \uc88b\uc740 \uc77c\uc815";
  return "\ubb34\ub9ac \uc5c6\ub294 \uac00\uc871\ud615 \uc77c\uc815";
}

function budgetHint(value) {
  if (value === "low") return "\uac00\uc131\ube44 \uc911\uc2ec \uc7a5\uc18c";
  if (value === "medium") return "\ube44\uc6a9\uacfc \ub9cc\uc871\ub3c4 \uade0\ud615";
  return "\uacbd\ud5d8\uacfc \ud3b8\uc548\ud568 \uc6b0\uc120";
}

function labelTimeSlot(value) {
  if (value === "morning") return "\uc624\uc804";
  if (value === "afternoon") return "\uc624\ud6c4";
  if (value === "evening") return "\uc800\ub141";
  return value;
}

function groupByDay(items) {
  const map = new Map();
  items.forEach((item) => {
    if (!map.has(item.day_number)) map.set(item.day_number, []);
    map.get(item.day_number).push(item);
  });
  return Array.from(map.entries()).sort((a, b) => a[0] - b[0]);
}

export function RulePlanner() {
  const [form, setForm] = useState(initialForm);
  const [catalog, setCatalog] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [currentStep, setCurrentStep] = useState(1);

  useEffect(() => {
    const loadOptions = async () => {
      setCatalogLoading(true);
      try {
        const data = await apiClient.get("/rule-itinerary/options");
        setCatalog(data?.cities ?? []);
      } catch (err) {
        setError(err.message || "\ub3c4\uc2dc \uc635\uc158\uc744 \ubd88\ub7ec\uc624\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.");
      } finally {
        setCatalogLoading(false);
      }
    };
    loadOptions();
  }, []);

  const groupedItems = useMemo(() => groupByDay(result?.items ?? []), [result]);
  const filteredCountries = useMemo(() => {
    if (!form.continent) return [...new Set(catalog.map((option) => option.country))];
    return [...new Set(catalog.filter((option) => option.continent === form.continent).map((option) => option.country))];
  }, [catalog, form.continent]);
  const filteredCities = useMemo(() => {
    return catalog.filter((option) => {
      if (form.continent && option.continent !== form.continent) return false;
      if (form.country && option.country !== form.country) return false;
      return true;
    });
  }, [catalog, form.continent, form.country]);

  const updateField = (name, value) => setForm((prev) => ({ ...prev, [name]: value }));

  const toggleConcept = (concept) => {
    setForm((prev) => {
      const has = prev.concepts.includes(concept);
      const next = has ? prev.concepts.filter((item) => item !== concept) : [...prev.concepts, concept];
      return { ...prev, concepts: next.length > 0 ? next : ["sightseeing"] };
    });
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const payload = {
        ...form,
        travelers: Number(form.travelers) || 2,
        budget_value: form.budget_value === "" ? null : Number(form.budget_value),
      };
      const data = await apiClient.post("/rule-itinerary/generate", payload);
      setResult(data);
      setMessage(`${data.city}\uc5d0 \ub300\ud55c \uc77c\uc815 ${data.items.length}\uac1c\uac00 \uc0dd\uc131\ub418\uc5c8\uc2b5\ub2c8\ub2e4.`);
      setCurrentStep(STEP_COUNT);
    } catch (err) {
      setError(err.message || "\uaddc\uce59\uae30\ubc18 \uc77c\uc815 \uc0dd\uc131\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="feature-shell">
      <div className="planner-steps">
        {[1, 2, 3, 4].map((step) => (
          <button
            key={step}
            type="button"
            className={`planner-step ${currentStep === step ? "is-active" : ""} ${currentStep > step ? "is-done" : ""}`}
            onClick={() => setCurrentStep(step)}
          >
            <span>{step}</span>
            <strong>
              {step === 1 ? TEXT.step1 : ""}
              {step === 2 ? TEXT.step2 : ""}
              {step === 3 ? TEXT.step3 : ""}
              {step === 4 ? TEXT.step4 : ""}
            </strong>
          </button>
        ))}
      </div>

      <div className="planner-layout">
        <section className="panel panel-featured planner-panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">{TEXT.plannerKicker}</p>
              <h2>{TEXT.plannerTitle}</h2>
            </div>
            <div className="pill-row">
              <span className="pill">/rule-itinerary/options</span>
              <span className="pill">/rule-itinerary/generate</span>
            </div>
          </div>

          {currentStep === 1 ? (
            <div className="planner-stage">
              <div className="stage-header">
                <h3>{TEXT.step1Title}</h3>
                <p>{TEXT.step1Desc}</p>
              </div>
              <div className="input-grid">
                <label className="field">
                  <span>{TEXT.continent}</span>
                  <select
                    value={form.continent}
                    onChange={(event) => {
                      updateField("continent", event.target.value);
                      updateField("country", "");
                    }}
                  >
                    <option value="">{TEXT.anyContinent}</option>
                    {[...new Set(catalog.map((option) => option.continent))].map((continent) => (
                      <option key={continent} value={continent}>{continent}</option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>{TEXT.country}</span>
                  <select value={form.country} onChange={(event) => updateField("country", event.target.value)}>
                    <option value="">{TEXT.anyCountry}</option>
                    {filteredCountries.map((country) => (
                      <option key={country} value={country}>{country}</option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>{TEXT.city}</span>
                  <select value={form.city} onChange={(event) => updateField("city", event.target.value)}>
                    {filteredCities.map((option) => (
                      <option key={`${option.country}-${option.city}`} value={option.city}>{option.city}</option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="catalog-preview-grid">
                {filteredCities.map((option) => (
                  <button
                    key={`${option.country}-${option.city}`}
                    type="button"
                    className={`mini-city-card ${form.city === option.city ? "is-selected" : ""}`}
                    onClick={() => {
                      updateField("continent", option.continent);
                      updateField("country", option.country);
                      updateField("city", option.city);
                    }}
                  >
                    <strong>{option.city}</strong>
                    <span>{option.country}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {currentStep === 2 ? (
            <div className="planner-stage">
              <div className="stage-header">
                <h3>{TEXT.step2Title}</h3>
                <p>{TEXT.step2Desc}</p>
              </div>
              <div className="input-grid">
                <label className="field">
                  <span>{TEXT.travelers}</span>
                  <input type="number" min="1" value={form.travelers} onChange={(event) => updateField("travelers", event.target.value)} />
                </label>
                <label className="field">
                  <span>{TEXT.duration}</span>
                  <input value={form.duration_label} onChange={(event) => updateField("duration_label", event.target.value)} placeholder="\u0032\ubc153\uc77c" />
                </label>
                <label className="field">
                  <span>{TEXT.budgetValue}</span>
                  <input type="number" min="0" value={form.budget_value} onChange={(event) => updateField("budget_value", event.target.value)} placeholder={TEXT.optional} />
                </label>
              </div>
              <div className="choice-grid">
                {budgetOptions.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={`choice-card ${form.budget_band === option ? "is-selected" : ""}`}
                    onClick={() => updateField("budget_band", option)}
                  >
                    <strong>{labelBudget(option)}</strong>
                    <span>{budgetHint(option)}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {currentStep === 3 ? (
            <div className="planner-stage">
              <div className="stage-header">
                <h3>{TEXT.step3Title}</h3>
                <p>{TEXT.step3Desc}</p>
              </div>
              <div className="field concept-field">
                <span>{TEXT.concepts}</span>
                <div className="chip-row">
                  {conceptOptions.map((concept) => (
                    <button key={concept} type="button" className={`chip ${form.concepts.includes(concept) ? "is-selected" : ""}`} onClick={() => toggleConcept(concept)}>
                      {labelConcept(concept)}
                    </button>
                  ))}
                </div>
              </div>
              <div className="choice-grid">
                {styleOptions.map((option) => (
                  <button key={option} type="button" className={`choice-card ${form.style === option ? "is-selected" : ""}`} onClick={() => updateField("style", option)}>
                    <strong>{labelStyle(option)}</strong>
                    <span>{labelStyleDesc(option)}</span>
                  </button>
                ))}
              </div>
              <div className="choice-grid">
                {companionOptions.map((option) => (
                  <button key={option} type="button" className={`choice-card ${form.companion_type === option ? "is-selected" : ""}`} onClick={() => updateField("companion_type", option)}>
                    <strong>{labelCompanion(option)}</strong>
                    <span>{labelCompanionDesc(option)}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {currentStep === 4 ? (
            <div className="planner-stage">
              <div className="stage-header">
                <h3>{TEXT.step4Title}</h3>
                <p>{TEXT.step4Desc}</p>
              </div>
              <div className="review-grid">
                <div className="review-card">
                  <span>{TEXT.city}</span>
                  <strong>{form.city || TEXT.autoSelect}</strong>
                  <small>{form.country || TEXT.anyCountry} / {form.continent || TEXT.anyContinent}</small>
                </div>
                <div className="review-card">
                  <span>{TEXT.duration}</span>
                  <strong>{form.duration_label || "\u0032\ubc153\uc77c"}</strong>
                  <small>{form.travelers}\uba85</small>
                </div>
                <div className="review-card">
                  <span>{TEXT.budgetValue}</span>
                  <strong>{labelBudget(form.budget_band)}</strong>
                  <small>{form.budget_value === "" ? TEXT.noDirectBudget : `${TEXT.enteredBudgetPrefix} ${form.budget_value}`}</small>
                </div>
                <div className="review-card">
                  <span>{TEXT.step3}</span>
                  <strong>{labelStyle(form.style)}</strong>
                  <small>{form.concepts.map(labelConcept).join(", ")}</small>
                </div>
              </div>
              <div className="action-row">
                <button onClick={handleGenerate} disabled={loading}>
                  {loading ? TEXT.generating : TEXT.generate}
                </button>
              </div>
            </div>
          ) : null}

          <div className="planner-nav">
            <button type="button" className="ghost-button" disabled={currentStep === 1} onClick={() => setCurrentStep((step) => Math.max(1, step - 1))}>
              {TEXT.previous}
            </button>
            <button type="button" className="ghost-button" disabled={currentStep === STEP_COUNT} onClick={() => setCurrentStep((step) => Math.min(STEP_COUNT, step + 1))}>
              {TEXT.next}
            </button>
          </div>

          <div className="status-row">
            <div className="status-box">
              <span className="status-title">{TEXT.catalog}</span>
              <strong>{catalogLoading ? TEXT.loadingCities : `${catalog.length}\uac1c \ub3c4\uc2dc`}</strong>
            </div>
            <div className="status-box">
              <span className="status-title">{TEXT.currentCity}</span>
              <strong>{result?.city || form.city || TEXT.notSelected}</strong>
            </div>
          </div>

          {message ? <p className="feedback success">{message}</p> : null}
          {error ? <p className="feedback error">{error}</p> : null}
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">{TEXT.resultKicker}</p>
              <h2>{TEXT.resultTitle}</h2>
            </div>
          </div>

          {groupedItems.length > 0 ? (
            <div className="day-grid">
              {groupedItems.map(([dayNumber, items]) => (
                <article key={dayNumber} className="day-card">
                  <h3>{dayNumber}\uc77c\ucc28</h3>
                  {items.map((item) => (
                    <div key={`${dayNumber}-${item.time_slot}-${item.place_name}`} className="slot-row">
                      <strong>{labelTimeSlot(item.time_slot)}</strong>
                      <span>{item.place_name}</span>
                      <small>{item.area}</small>
                      <p>{item.notes}</p>
                    </div>
                  ))}
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <h3>{TEXT.emptyTitle}</h3>
              <p>{TEXT.emptyDesc}</p>
            </div>
          )}

          <details className="raw-panel">
            <summary>{TEXT.rawJson}</summary>
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </details>
        </section>
      </div>
    </section>
  );
}
