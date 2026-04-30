import { TripCard } from "./trip-card";
import { TripSummaryItem } from "../../../shared/types/domain";

type TripListProps = {
  trips: TripSummaryItem[];
  onToggleFavorite: (tripId: string, nextFavorite: boolean) => void;
  pendingTripId?: string | null;
};

export function TripList({ trips, onToggleFavorite, pendingTripId }: TripListProps) {
  return (
    <div className="card card-tinted">
      <div className="section-header">
        <div>
          <span className="section-kicker">Planner archive</span>
          <h2 className="section-title" style={{ fontSize: "1.7rem", marginBottom: 6 }}>
            Saved itineraries
          </h2>
          <p className="section-subtitle">Recent trips, drafts, and shared plans in one view.</p>
        </div>
      </div>

      <div className="trip-list">
        {trips.map((trip) => (
          <TripCard
            key={trip.id}
            pending={pendingTripId === trip.id}
            trip={trip}
            onToggleFavorite={onToggleFavorite}
          />
        ))}
      </div>
    </div>
  );
}
