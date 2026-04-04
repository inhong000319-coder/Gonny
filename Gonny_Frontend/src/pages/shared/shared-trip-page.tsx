import { PublicLayout } from "../../app/layouts/public-layout";

function GlobeIcon() {
  return (
    <svg aria-hidden="true" className="landing-feature-icon" fill="none" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4 12h16M12 4a12 12 0 0 1 0 16M12 4a12 12 0 0 0 0 16" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

export function SharedTripPage() {
  return (
    <PublicLayout>
      <section className="page-hero panel panel-gradient">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <span className="section-kicker">Shared itinerary</span>
            <h1 className="section-title" style={{ fontSize: "2.2rem", margin: "8px 0" }}>
              Jeju 2N3D
            </h1>
            <p className="section-subtitle" style={{ marginBottom: 0 }}>
              A clean public-facing view for people opening the plan from a shared link.
            </p>
          </div>
          <div className="landing-feature-icon-wrap">
            <GlobeIcon />
          </div>
        </div>
      </section>

      <div className="card card-tinted stack">
        <div className="timeline">
          <div className="timeline-item timeline-item-accent">09:00 Seongsan Ilchulbong</div>
          <div className="timeline-item timeline-item-accent">11:30 Black Pork Lunch</div>
          <div className="timeline-item timeline-item-accent">14:00 Cafe Stop</div>
        </div>
      </div>
    </PublicLayout>
  );
}
