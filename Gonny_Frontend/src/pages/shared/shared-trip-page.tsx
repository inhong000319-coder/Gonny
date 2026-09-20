import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { PublicLayout } from "../../app/layouts/public-layout";
import { SharedItineraryItem } from "../../features/share/api/get-shared-trip";
import { useSharedTripQuery } from "../../features/share/hooks/use-shared-trip-query";

function GlobeIcon() {
  return (
    <svg aria-hidden="true" className="landing-feature-icon" fill="none" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4 12h16M12 4a12 12 0 0 1 0 16M12 4a12 12 0 0 0 0 16" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

const timeSlotLabelKo: Record<string, string> = {
  morning: "오전",
  afternoon: "오후",
  evening: "저녁",
};

function labelTimeSlot(value: string) {
  return timeSlotLabelKo[value] ?? value;
}

function groupByDay(items: SharedItineraryItem[]) {
  return items.reduce<Array<{ day: number; items: SharedItineraryItem[] }>>((groups, item) => {
    const current = groups.find((group) => group.day === item.day_number);
    if (current) {
      current.items.push(item);
      return groups;
    }

    groups.push({ day: item.day_number, items: [item] });
    return groups;
  }, []).sort((left, right) => left.day - right.day);
}

export function SharedTripPage() {
  const { token = "" } = useParams();
  const { data, isLoading, isError } = useSharedTripQuery(token);
  const groupedItems = useMemo(() => groupByDay(data?.itinerary_items ?? []), [data]);

  if (isLoading) {
    return (
      <PublicLayout>
        <div className="card">
          <h2 className="section-title">공유된 일정을 불러오는 중이에요.</h2>
        </div>
      </PublicLayout>
    );
  }

  if (isError || !data) {
    return (
      <PublicLayout>
        <div className="card">
          <h2 className="section-title">링크가 만료되었거나 존재하지 않습니다.</h2>
          <p className="section-subtitle" style={{ marginBottom: 0 }}>
            공유한 분에게 새 링크를 요청해 주세요.
          </p>
        </div>
      </PublicLayout>
    );
  }

  return (
    <PublicLayout>
      <section className="page-hero panel panel-gradient">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <span className="section-kicker">Shared itinerary</span>
            <h1 className="section-title" style={{ fontSize: "2.2rem", margin: "8px 0" }}>
              {data.title}
            </h1>
            <p className="section-subtitle" style={{ marginBottom: 0 }}>
              {data.destination} · {data.start_date} ~ {data.end_date}
            </p>
          </div>
          <div className="landing-feature-icon-wrap">
            <GlobeIcon />
          </div>
        </div>
      </section>

      <div className="card card-tinted stack">
        {groupedItems.length > 0 ? (
          groupedItems.map((group) => (
            <div className="stack" key={group.day}>
              <strong className="trip-card-title">DAY {group.day}</strong>
              <div className="timeline">
                {group.items.map((item) => (
                  <div className="timeline-item timeline-item-accent" key={item.id}>
                    {labelTimeSlot(item.time_slot)} · {item.place_name}
                  </div>
                ))}
              </div>
            </div>
          ))
        ) : (
          <p className="section-subtitle" style={{ marginBottom: 0 }}>
            아직 등록된 일정이 없어요.
          </p>
        )}
      </div>
    </PublicLayout>
  );
}
