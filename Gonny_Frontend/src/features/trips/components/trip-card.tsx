import { Link } from "react-router-dom";
import { Badge } from "../../../shared/components/ui/badge";
import { TripSummaryItem } from "../../../shared/types/domain";

type TripCardProps = { trip: TripSummaryItem; pending?: boolean; onToggleFavorite: (tripId: string, nextFavorite: boolean) => void };

const statusLabelMap = { upcoming: "예정", ongoing: "진행 중", completed: "완료" } as const;

export function TripCard({ trip, pending = false, onToggleFavorite }: TripCardProps) {
  return (
    <article className="tl-card">
      <div className="tl-card-header">
        <div><span className="tl-card-destination">{trip.destination}</span><h3>{trip.title}</h3></div>
        <Badge>{statusLabelMap[trip.status]}</Badge>
      </div>
      <p className="tl-card-date">{trip.startDate} - {trip.endDate}</p>
      {trip.accommodationLabel ? <p className="tl-card-date">숙소 {trip.accommodationLabel}</p> : null}
      <div className="tl-card-meta"><span>예산 {trip.budget.toLocaleString()}원</span><span>동행 {trip.companionCount}명</span></div>
      <div className="tl-card-actions">
        <Link className="text-link" to={`/trips/${trip.id}`}>일정 보기</Link>
        <Link className="text-link" to={`/trips/${trip.id}/memory`}>기록 보기</Link>
        <button className={`tl-save-button ${trip.isFavorite ? "is-saved" : ""}`} disabled={pending} onClick={() => onToggleFavorite(trip.id, !trip.isFavorite)} type="button">
          {trip.isFavorite ? "저장됨" : "저장하기"}
        </button>
      </div>
    </article>
  );
}
