import { Link } from "react-router-dom";
import { Badge } from "../../../shared/components/ui/badge";
import { TripSummaryItem } from "../../../shared/types/domain";

function TripCardIcon() {
  return (
    <svg aria-hidden="true" className="trip-card-icon" fill="none" viewBox="0 0 24 24">
      <path
        d="M4 7.5 9 5l6 2.5L20 5v12l-5 2-6-2-5 2v-12Z"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path d="M9 5v12M15 7.5v12" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

type TripCardProps = {
  trip: TripSummaryItem;
};

const statusLabelMap = {
  upcoming: "예정",
  ongoing: "진행 중",
  completed: "완료",
} as const;

export function TripCard({ trip }: TripCardProps) {
  return (
    <Link className="trip-card trip-card-polished" to={`/trips/${trip.id}`}>
      <div className="trip-card-main">
        <div className="trip-card-icon-wrap">
          <TripCardIcon />
        </div>

        <div className="trip-card-copy">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong className="trip-card-title">{trip.title}</strong>
            <Badge>{statusLabelMap[trip.status]}</Badge>
          </div>
          <p className="section-subtitle" style={{ margin: "8px 0 0" }}>
            {trip.startDate} - {trip.endDate}
          </p>
          <div className="trip-card-meta">
            <span>{trip.destination}</span>
            <span>예산 {trip.budget.toLocaleString()}원</span>
            <span>동행 {trip.companionCount}명</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
