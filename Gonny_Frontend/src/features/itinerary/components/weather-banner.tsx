import { Button } from "../../../shared/components/ui/button";

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

export function WeatherBanner() {
  return (
    <div className="weather-banner">
      <div className="weather-banner-icon">
        <CloudRainIcon />
      </div>
      <div className="weather-banner-copy">
        <h3 className="section-title" style={{ marginBottom: 6 }}>
          Rain alert for Day 2 afternoon
        </h3>
        <p className="section-subtitle" style={{ marginBottom: 0 }}>
          12 mm precipitation expected. This is a good place to surface indoor alternatives and
          keep the user in control instead of auto-changing the itinerary.
        </p>
      </div>
      <div className="weather-banner-actions">
        <Button variant="secondary">Keep current plan</Button>
        <Button>See AI alternatives</Button>
      </div>
    </div>
  );
}
