import { useMemo, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { PublicLayout } from "../../app/layouts/public-layout";
import { SharedItineraryItem } from "../../features/share/api/get-shared-trip";
import { useSharedTripQuery } from "../../features/share/hooks/use-shared-trip-query";
import { formatSharedAccommodationLines } from "../../features/trips/utils/format-accommodation-label";
import { useDocumentTitle } from "../../shared/hooks/use-document-title";
import "./shared-trip-page.css";

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
  useDocumentTitle(data?.title);
  const groupedItems = useMemo(() => groupByDay(data?.itinerary_items ?? []), [data]);
  const accommodationLines = useMemo(
    () =>
      formatSharedAccommodationLines(
        (data?.stays ?? []).map((stay) => ({
          startNight: stay.start_night,
          nights: stay.nights,
          accommodationName: stay.accommodation_name,
          accommodationType: stay.accommodation_type,
        })),
      ),
    [data],
  );

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
      <section className="page-hero panel">
        <h1 className="sp-title">{data.title}</h1>
        <p className="sp-meta">
          {data.destination} · {data.start_date} ~ {data.end_date}
        </p>
        {accommodationLines.map((line) => (
          <p className="sp-meta" key={line}>
            {line}
          </p>
        ))}
      </section>

      <div className="card sp-timeline-card">
        {groupedItems.length > 0 ? (
          groupedItems.map((group) => {
            const dayIndex = ((group.day - 1) % 6) + 1;
            const dayColorStyle = {
              "--day-color": `var(--day-${dayIndex})`,
              "--day-color-text": `var(--day-${dayIndex}-text)`,
            } as CSSProperties;

            return (
              <div className="sp-day" key={group.day} style={dayColorStyle}>
                <strong className="sp-day-title">DAY {group.day}</strong>
                <div className="sp-item-list">
                  {group.items.map((item) => (
                    <p className="sp-item" key={item.id}>
                      <span className="sp-item-time">{labelTimeSlot(item.time_slot)}</span>
                      {item.place_name}
                    </p>
                  ))}
                </div>
              </div>
            );
          })
        ) : (
          <p className="section-subtitle" style={{ marginBottom: 0 }}>
            아직 등록된 일정이 없어요.
          </p>
        )}
      </div>
    </PublicLayout>
  );
}
