import { Link } from "react-router-dom";
import { Badge } from "../../../shared/components/ui/badge";
import { TripSummaryItem } from "../../../shared/types/domain";

type TripCardProps = { trip: TripSummaryItem; pending?: boolean; onToggleFavorite: (tripId: string, nextFavorite: boolean) => void };

const statusLabelMap = { upcoming: "예정", ongoing: "진행 중", completed: "완료" } as const;

export function TripCard({ trip, pending = false, onToggleFavorite }: TripCardProps) {
  return (
    <article className="trip-card trip-card-polished">
      <div className="trip-card-map-mark"><span>{trip.destination.slice(0, 1).toUpperCase()}</span></div>
      <div className="trip-card-copy">
        <div className="trip-card-title-row"><div><span className="trip-card-destination">{trip.destination}</span><h3>{trip.title}</h3></div><Badge>{statusLabelMap[trip.status]}</Badge></div>
        <p className="trip-card-date">{trip.startDate} - {trip.endDate}</p>
        <div className="trip-card-meta"><span>예산 {trip.budget.toLocaleString()}원</span><span>동행 {trip.companionCount}명</span></div>
        <div className="trip-card-actions">
          <Link className="text-link" to={`/trips/${trip.id}`}>일정 보기</Link>
          <Link className="text-link" to={`/trips/${trip.id}/memory`}>기록 보기</Link>
          <button className={`trip-save-button ${trip.isFavorite ? "saved" : ""}`} disabled={pending} onClick={() => onToggleFavorite(trip.id, !trip.isFavorite)} type="button">
            {trip.isFavorite ? "저장됨" : "저장하기"}
          </button>
        </div>
      </div>
    </article>
  );
}
