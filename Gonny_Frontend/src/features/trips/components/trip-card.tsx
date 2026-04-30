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
  pending?: boolean;
  onToggleFavorite: (tripId: string, nextFavorite: boolean) => void;
};

const statusLabelMap = {
  upcoming: "예정",
  ongoing: "진행 중",
  completed: "완료",
} as const;

export function TripCard({ trip, pending = false, onToggleFavorite }: TripCardProps) {
  return (
    <article className="trip-card trip-card-polished">
      <div className="trip-card-main">
        <div className="trip-card-icon-wrap">
          <TripCardIcon />
        </div>

        <div className="trip-card-copy">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong className="trip-card-title">{trip.title}</strong>
            <div className="row">
              <button
                className={`chip trip-favorite-chip ${trip.isFavorite ? "active" : ""}`}
                disabled={pending}
                onClick={() => onToggleFavorite(trip.id, !trip.isFavorite)}
                type="button"
              >
                {trip.isFavorite ? "즐겨찾기 해제" : "즐겨찾기"}
              </button>
              <Badge>{statusLabelMap[trip.status]}</Badge>
            </div>
          </div>
          <p className="section-subtitle" style={{ margin: "8px 0 0" }}>
            {trip.startDate} - {trip.endDate}
          </p>
          <div className="trip-card-meta">
            <span>{trip.destination}</span>
            <span>예산 {trip.budget.toLocaleString()}원</span>
            <span>동행 {trip.companionCount}명</span>
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <Link to={`/trips/${trip.id}`}>
              <button className="button secondary" type="button">
                여행 상세 보기
              </button>
            </Link>
            <Link to={`/trips/${trip.id}/memory`}>
              <button className="button secondary" type="button">
                기록관리 보기
              </button>
            </Link>
            {trip.isFavorite ? <span className="chip active">프로필에 표시 중</span> : null}
          </div>
        </div>
      </div>
    </article>
  );
}
