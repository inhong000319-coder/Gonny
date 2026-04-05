import { useMemo, useState } from "react";

import { apiClient } from "../../api/client";

const TEXT = {
  kicker: "\uae30\uc874 \ubc31\uc5d4\ub4dc \ud750\ub984",
  title: "\uc5ec\ud589 \uc0dd\uc131 \ubc0f AI \uc77c\uc815 \ud14c\uc2a4\ud2b8",
  destination: "\ubaa9\uc801\uc9c0",
  startDate: "\ucd9c\ubc1c\uc77c",
  endDate: "\uc885\ub8cc\uc77c",
  budget: "\uc608\uc0b0",
  style: "\uc5ec\ud589 \uc2a4\ud0c0\uc77c",
  companion: "\ub3d9\ud589 \uc720\ud615",
  createTrip: "\uc5ec\ud589 \uc0dd\uc131",
  getTrips: "\uc5ec\ud589 \ubaa9\ub85d \uc870\ud68c",
  generate: "\uc77c\uc815 \uc0dd\uc131",
  detail: "\uc5ec\ud589 \uc0c1\uc138 \uc870\ud68c",
  tripId: "\ud604\uc7ac \u0054\u0072\u0069\u0070 \u0049\u0044",
  loading: "\ub85c\ub529 \uc0c1\ud0dc",
  none: "\uc5c6\uc74c",
  running: "\ucc98\ub9ac \uc911",
  idle: "\ub300\uae30 \uc911",
  savedTrips: "\uc800\uc7a5\ub41c \uc5ec\ud589",
  tripList: "\uc5ec\ud589 \ubaa9\ub85d",
  groupedResult: "\ubb36\uc74c \uacb0\uacfc",
  preview: "\uc77c\uc815 \ubbf8\ub9ac\ubcf4\uae30",
  rawJson: "\uc6d0\ubcf8 \u004a\u0053\u004f\u004e \ubcf4\uae30",
  unknownDestination: "\ubaa9\uc801\uc9c0 \uc5c6\uc74c",
  loadTripsHint: "\uc5ec\ud589 \ubaa9\ub85d\uc744 \uc870\ud68c\ud558\uba74 \uc800\uc7a5\ub41c trip \ub370\uc774\ud130\uac00 \uc5ec\uae30\uc5d0 \ud45c\uc2dc\ub429\ub2c8\ub2e4.",
  previewHint: "\uc5ec\ud589\uc744 \uc0dd\uc131\ud558\uace0 \uc0c1\uc138 \uc870\ud68c\ub97c \ud558\uba74 itinerary \ud56d\ubaa9\uc744 \uc5ec\uae30\uc11c \ud655\uc778\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
  requestError: "\uc694\uccad \ucc98\ub9ac \uc911 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4.",
  selectTripFirst: "\uba3c\uc800 \uc5ec\ud589\uc744 \uc0dd\uc131\ud558\uac70\ub098 \ubaa9\ub85d\uc5d0\uc11c \uc120\ud0dd\ud574 \uc8fc\uc138\uc694.",
};

const initialForm = {
  destination: "Tokyo",
  start_date: "2026-04-10",
  end_date: "2026-04-12",
  budget: 1200000,
  travel_style: "relax",
  companion_type: "friend",
};

function extractTripId(data) {
  return data?.trip_id ?? data?.id ?? data?.trip?.trip_id ?? data?.trip?.id ?? "";
}

function normalizeTripList(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.trips)) return data.trips;
  if (Array.isArray(data?.items)) return data.items;
  return [];
}

function normalizeItineraryItems(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.itinerary_items)) return data.itinerary_items;
  if (Array.isArray(data?.detail?.itinerary_items)) return data.detail.itinerary_items;
  if (Array.isArray(data?.trip?.itinerary_items)) return data.trip.itinerary_items;
  return [];
}

function groupItemsByDay(items) {
  const grouped = {};
  items.forEach((item, index) => {
    const rawDay = item?.day_number ?? item?.day ?? index + 1;
    const rawTime = item?.time_slot ?? item?.time_of_day ?? item?.period ?? "schedule";
    const rawPlace = item?.place_name ?? item?.title ?? item?.location ?? "\uc7a5\uc18c \uc5c6\uc74c";
    const dayKey = typeof rawDay === "number" || /^\d+$/.test(String(rawDay)) ? `${rawDay}\uc77c\ucc28` : `${index + 1}\uc77c\ucc28`;

    if (!grouped[dayKey]) grouped[dayKey] = [];
    grouped[dayKey].push({ time: String(rawTime).toLowerCase(), place: rawPlace, notes: item?.notes || "" });
  });
  return Object.entries(grouped);
}

export function AiTripTester() {
  const [form, setForm] = useState(initialForm);
  const [tripId, setTripId] = useState("");
  const [tripDetail, setTripDetail] = useState(null);
  const [tripList, setTripList] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const groupedItinerary = useMemo(() => groupItemsByDay(normalizeItineraryItems(tripDetail)), [tripDetail]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: name === "budget" ? Number(value) : value }));
  };

  const withStatus = async (action) => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      await action();
    } catch (err) {
      setError(err.message || TEXT.requestError);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTrip = () =>
    withStatus(async () => {
      const data = await apiClient.post("/trips", form);
      const newTripId = extractTripId(data);
      setTripId(String(newTripId));
      setTripDetail(data);
      setMessage(`\uc5ec\ud589\uc774 \uc0dd\uc131\ub418\uc5c8\uc2b5\ub2c8\ub2e4. trip_id: ${newTripId}`);
    });

  const handleGetTrips = () =>
    withStatus(async () => {
      const data = await apiClient.get("/trips");
      const list = normalizeTripList(data);
      setTripList(list);
      setMessage(`\uc5ec\ud589 \ubaa9\ub85d ${list.length}\uac74\uc744 \ubd88\ub7ec\uc654\uc2b5\ub2c8\ub2e4.`);
    });

  const handleGenerateItinerary = () => {
    if (!tripId) {
      setError(TEXT.selectTripFirst);
      return;
    }

    withStatus(async () => {
      await apiClient.post(`/trips/${tripId}/generate-itinerary`);
      setMessage("\u0041\u0049 \uc77c\uc815 \uc0dd\uc131 \uc694\uccad\uc744 \ubcf4\ub0c8\uc2b5\ub2c8\ub2e4.");
    });
  };

  const handleGetTripDetail = () => {
    if (!tripId) {
      setError(TEXT.selectTripFirst);
      return;
    }

    withStatus(async () => {
      const data = await apiClient.get(`/trips/${tripId}`);
      setTripDetail(data);
      setMessage("\uc5ec\ud589 \uc0c1\uc138 \uc815\ubcf4\ub97c \ubd88\ub7ec\uc654\uc2b5\ub2c8\ub2e4.");
    });
  };

  return (
    <section className="feature-shell">
      <div className="panel">
        <div className="panel-heading">
          <div>
            <p className="panel-kicker">{TEXT.kicker}</p>
            <h2>{TEXT.title}</h2>
          </div>
          <div className="pill-row">
            <span className="pill">/trips</span>
            <span className="pill">/generate-itinerary</span>
          </div>
        </div>

        <div className="input-grid">
          <label className="field"><span>{TEXT.destination}</span><input name="destination" value={form.destination} onChange={handleChange} /></label>
          <label className="field"><span>{TEXT.startDate}</span><input type="date" name="start_date" value={form.start_date} onChange={handleChange} /></label>
          <label className="field"><span>{TEXT.endDate}</span><input type="date" name="end_date" value={form.end_date} onChange={handleChange} /></label>
          <label className="field"><span>{TEXT.budget}</span><input type="number" name="budget" value={form.budget} onChange={handleChange} /></label>
          <label className="field"><span>{TEXT.style}</span><input name="travel_style" value={form.travel_style} onChange={handleChange} /></label>
          <label className="field"><span>{TEXT.companion}</span><input name="companion_type" value={form.companion_type} onChange={handleChange} /></label>
        </div>

        <div className="action-row">
          <button onClick={handleCreateTrip} disabled={loading}>{TEXT.createTrip}</button>
          <button onClick={handleGetTrips} disabled={loading}>{TEXT.getTrips}</button>
          <button onClick={handleGenerateItinerary} disabled={loading || !tripId}>{TEXT.generate}</button>
          <button onClick={handleGetTripDetail} disabled={loading || !tripId}>{TEXT.detail}</button>
        </div>

        <div className="status-row">
          <div className="status-box">
            <span className="status-title">{TEXT.tripId}</span>
            <strong>{tripId || TEXT.none}</strong>
          </div>
          <div className="status-box">
            <span className="status-title">{TEXT.loading}</span>
            <strong>{loading ? TEXT.running : TEXT.idle}</strong>
          </div>
        </div>

        {message ? <p className="feedback success">{message}</p> : null}
        {error ? <p className="feedback error">{error}</p> : null}
      </div>

      <div className="two-column-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">{TEXT.savedTrips}</p>
              <h2>{TEXT.tripList}</h2>
            </div>
          </div>

          {tripList.length > 0 ? (
            <div className="stack-list">
              {tripList.map((trip, index) => {
                const currentTripId = extractTripId(trip) || `unknown-${index}`;
                return (
                  <button
                    key={currentTripId}
                    type="button"
                    className="list-card"
                    onClick={() => {
                      setTripId(String(currentTripId));
                      setMessage(`trip_id ${currentTripId}\ub97c \uc120\ud0dd\ud588\uc2b5\ub2c8\ub2e4.`);
                      setError("");
                    }}
                  >
                    <strong>{trip?.destination || TEXT.unknownDestination}</strong>
                    <span>trip_id: {currentTripId}</span>
                    <span>{trip?.start_date || "?"} ~ {trip?.end_date || "?"}</span>
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="empty-text">{TEXT.loadTripsHint}</p>
          )}
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">{TEXT.groupedResult}</p>
              <h2>{TEXT.preview}</h2>
            </div>
          </div>

          {groupedItinerary.length > 0 ? (
            <div className="day-grid">
              {groupedItinerary.map(([day, items]) => (
                <article key={day} className="day-card">
                  <h3>{day}</h3>
                  {items.map((item, index) => (
                    <div key={`${day}-${item.time}-${index}`} className="slot-row">
                      <strong>{item.time}</strong>
                      <span>{item.place}</span>
                      {item.notes ? <p>{item.notes}</p> : null}
                    </div>
                  ))}
                </article>
              ))}
            </div>
          ) : (
            <p className="empty-text">{TEXT.previewHint}</p>
          )}

          <details className="raw-panel">
            <summary>{TEXT.rawJson}</summary>
            <pre>{JSON.stringify(tripDetail, null, 2)}</pre>
          </details>
        </section>
      </div>
    </section>
  );
}
