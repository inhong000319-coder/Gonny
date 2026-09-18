import { useState } from "react";
import { Button } from "../../../shared/components/ui/button";

// Structurally mirrors the backend's RuleWeatherAlert
// (day_number/condition/precipitation_mm/affected_place_names/
// suggested_alternatives) - kept local rather than imported from
// trip-create-form.tsx, same pattern as shared/itinerary-export.ts's
// own local ItineraryItem/ExportLabels types.
type RuleWeatherAlert = {
  day_number: number;
  condition: "rain" | "snow";
  precipitation_mm: number;
  affected_place_names: string[];
  suggested_alternatives: string[];
};

type WeatherBannerProps = {
  alert: RuleWeatherAlert;
};

function CloudRainIcon() {
  return (
    <svg aria-hidden="true" className="status-icon" fill="none" viewBox="0 0 24 24">
      <path
        d="M8 18h8a4 4 0 0 0 .52-7.97A5.5 5.5 0 0 0 6 11a3.5 3.5 0 0 0 2 7Z"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path d="M9 18.8 8 21M12 18.8 11 21M15 18.8 14 21" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function conditionLabel(condition: RuleWeatherAlert["condition"]) {
  return condition === "snow" ? "눈" : "비";
}

export function WeatherBanner({ alert }: WeatherBannerProps) {
  const [showAlternatives, setShowAlternatives] = useState(false);

  return (
    <div className="weather-banner">
      <div className="weather-banner-icon">
        <CloudRainIcon />
      </div>
      <div className="weather-banner-copy">
        <h3 className="section-title" style={{ marginBottom: 6 }}>
          {alert.day_number}일차, {conditionLabel(alert.condition)} 예보가 있어요
        </h3>
        <p className="section-subtitle" style={{ marginBottom: 8 }}>
          예상 강수량 {alert.precipitation_mm}mm. 일정은 자동으로 바뀌지 않아요 - 실내 대안을 참고해서 직접
          정해보세요.
        </p>
        {alert.affected_place_names.length > 0 ? (
          <div className="planner-result-tags">
            {alert.affected_place_names.map((placeName) => (
              <span className="badge" key={placeName}>
                {placeName}
              </span>
            ))}
          </div>
        ) : null}
      </div>
      <div className="weather-banner-actions">
        <Button onClick={() => setShowAlternatives(false)} type="button" variant="secondary">
          이 계획 유지
        </Button>
        <Button onClick={() => setShowAlternatives(true)} type="button">
          실내 대안 보기
        </Button>
      </div>
      {showAlternatives ? (
        <div className="weather-banner-alternatives">
          {alert.suggested_alternatives.length > 0 ? (
            alert.suggested_alternatives.map((placeName) => (
              <span className="badge" key={placeName}>
                {placeName}
              </span>
            ))
          ) : (
            <p className="section-subtitle" style={{ marginBottom: 0 }}>
              추천할 만한 실내 대안을 찾지 못했어요.
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
