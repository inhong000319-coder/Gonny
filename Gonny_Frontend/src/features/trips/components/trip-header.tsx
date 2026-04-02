import { Badge } from "../../../shared/components/ui/badge";
import { Button } from "../../../shared/components/ui/button";
import { TripOverview } from "../../../shared/types/domain";

function MapIcon() {
  return (
    <svg aria-hidden="true" className="landing-feature-icon" fill="none" viewBox="0 0 24 24">
      <path d="M4 6.5 9 4l6 2.5L20 4v13.5L15 20l-6-2.5L4 20V6.5Z" stroke="currentColor" strokeWidth="1.8" />
      <path d="M9 4v13.5M15 6.5V20" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

type TripHeaderProps = {
  trip: TripOverview;
};

export function TripHeader({ trip }: TripHeaderProps) {
  return (
    <div className="page-hero panel panel-gradient">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="stack" style={{ gap: 10 }}>
          <span className="section-kicker">Trip overview</span>
          <div className="row">
            <Badge>{trip.dateRangeLabel}</Badge>
            <Badge>{trip.destination}</Badge>
          </div>
          <h1 className="section-title" style={{ fontSize: "2.2rem", margin: 0 }}>
            {trip.title}
          </h1>
          <p className="section-subtitle" style={{ margin: 0, maxWidth: 680 }}>
            날씨, 예산, 공유, 회고까지 여행 상세에서 한 흐름으로 볼 수 있도록 정리한 화면입니다.
          </p>
        </div>
        <div className="row">
          <div className="landing-feature-icon-wrap">
            <MapIcon />
          </div>
          <Button variant="secondary">공유</Button>
          <Button variant="secondary">PDF 저장</Button>
        </div>
      </div>
    </div>
  );
}
