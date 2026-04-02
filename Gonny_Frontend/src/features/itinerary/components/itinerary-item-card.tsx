import { ItineraryItem } from "../../../shared/types/domain";
import { Button } from "../../../shared/components/ui/button";

type ItineraryItemCardProps = {
  item: ItineraryItem;
};

export function ItineraryItemCard({ item }: ItineraryItemCardProps) {
  return (
    <div className="timeline-item">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <strong>
          {item.time} {item.title}
        </strong>
        <div className="row">
          <Button variant="secondary">체크인</Button>
          <Button variant="ghost">대안 추천</Button>
          <Button variant="ghost">장소 바꾸기</Button>
        </div>
      </div>
      <p className="section-subtitle" style={{ margin: "8px 0" }}>
        {item.meta}
      </p>
      <p style={{ margin: 0 }}>AI 팁: {item.tip}</p>
    </div>
  );
}
