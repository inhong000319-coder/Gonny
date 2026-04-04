import { Badge } from "../../../shared/components/ui/badge";
import { DayPlan } from "../../../shared/types/domain";
import { ItineraryItemCard } from "./itinerary-item-card";

type DayTimelineProps = {
  dayPlan: DayPlan;
};

export function DayTimeline({ dayPlan }: DayTimelineProps) {
  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 16 }}>
        <div className="row">
          <h2 className="section-title" style={{ margin: 0 }}>
            {dayPlan.dayLabel}
          </h2>
          <Badge>{dayPlan.weatherLabel}</Badge>
        </div>
        <Badge>{dayPlan.totalTimeLabel}</Badge>
      </div>

      <div className="timeline">
        {dayPlan.items.map((item) => (
          <ItineraryItemCard item={item} key={item.id} />
        ))}
      </div>
    </div>
  );
}
