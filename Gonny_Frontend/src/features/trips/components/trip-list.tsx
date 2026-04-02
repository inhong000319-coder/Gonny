import { TripCard } from "./trip-card";
import { TripSummaryItem } from "../../../shared/types/domain";

type TripListProps = {
  trips: TripSummaryItem[];
};

export function TripList({ trips }: TripListProps) {
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
          <TripCard key={trip.id} trip={trip} />
        ))}
      </div>
    </div>
  );
}
