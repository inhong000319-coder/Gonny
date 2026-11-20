import { Badge } from "../../../shared/components/ui/badge";
import { Button } from "../../../shared/components/ui/button";
import { TripOverview } from "../../../shared/types/domain";

type TripHeaderProps = {
  trip: TripOverview;
};

export function TripHeader({ trip }: TripHeaderProps) {
  return (
    <div className="page-hero panel">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="stack" style={{ gap: 10 }}>
          <div className="row">
            <Badge>{trip.dateRangeLabel}</Badge>
            <Badge>{trip.destination}</Badge>
            {trip.accommodationLabel ? <Badge>숙소: {trip.accommodationLabel}</Badge> : null}
          </div>
          <h1 className="section-title" style={{ fontSize: "2.2rem", margin: 0 }}>
            {trip.title}
          </h1>
          <p className="section-subtitle" style={{ margin: 0, maxWidth: 680 }}>
            날씨, 예산, 공유, 회고까지 여행 상세에서 한 흐름으로 볼 수 있도록 정리한 화면입니다.
          </p>
        </div>
        <div className="row">
          <Button variant="secondary">공유</Button>
          <Button variant="secondary">PDF 저장</Button>
        </div>
      </div>
    </div>
  );
}
