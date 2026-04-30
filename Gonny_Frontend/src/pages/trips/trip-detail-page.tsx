import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { queryKeys } from "../../shared/api/query-keys";
import { BudgetSummaryCard } from "../../features/budget/components/budget-summary-card";
import { ExpenseList } from "../../features/budget/components/expense-list";
import { useBudgetSummaryQuery } from "../../features/budget/hooks/use-budget-summary-query";
import { useExpensesQuery } from "../../features/budget/hooks/use-expenses-query";
import { createItineraryItem } from "../../features/itinerary/api/create-itinerary-item";
import { deleteItineraryItem } from "../../features/itinerary/api/delete-itinerary-item";
import { updateItineraryItem } from "../../features/itinerary/api/update-itinerary-item";
import { WeatherBanner } from "../../features/itinerary/components/weather-banner";
import { ReportInsights } from "../../features/report/components/report-insights";
import { ReportSummary } from "../../features/report/components/report-summary";
import { ShareLinkModal } from "../../features/share/components/share-link-modal";
import { TripHeader } from "../../features/trips/components/trip-header";
import { TripSummary } from "../../features/trips/components/trip-summary";
import { useTripDetailQuery } from "../../features/trips/hooks/use-trip-detail-query";
import { mockReportOverview } from "../../shared/mocks/trip-data";

type EditableItineraryItem = {
  id: number;
  day_number: number;
  time_slot: string;
  place_name: string;
  category: string;
  notes: string;
};

const timeSlotOptions = [
  { value: "morning", label: "오전" },
  { value: "afternoon", label: "오후" },
  { value: "evening", label: "저녁" },
];

const categoryOptions = ["관광", "식사", "카페", "쇼핑", "산책", "휴식", "체험"];

export function TripDetailPage() {
  const { tripId = "101" } = useParams();
  const queryClient = useQueryClient();
  const { data: tripDetail } = useTripDetailQuery(tripId);
  const { data: budget } = useBudgetSummaryQuery(tripId);
  const { data: expenses = [] } = useExpensesQuery(tripId);
  const [editableItems, setEditableItems] = useState<EditableItineraryItem[]>([]);
  const [newItem, setNewItem] = useState<EditableItineraryItem>({
    id: 0,
    day_number: 1,
    time_slot: "morning",
    place_name: "",
    category: "관광",
    notes: "",
  });

  useEffect(() => {
    if (!tripDetail) {
      return;
    }
    setEditableItems(
      tripDetail.itineraryItems.map((item) => ({
        id: item.id,
        day_number: item.day_number,
        time_slot: item.time_slot,
        place_name: item.place_name,
        category: item.category,
        notes: item.notes ?? "",
      })),
    );
  }, [tripDetail]);

  const itineraryByDay = useMemo(() => {
    return editableItems.reduce<Record<number, EditableItineraryItem[]>>((acc, item) => {
      if (!acc[item.day_number]) {
        acc[item.day_number] = [];
      }
      acc[item.day_number].push(item);
      return acc;
    }, {});
  }, [editableItems]);

  const createMutation = useMutation({
    mutationFn: () =>
      createItineraryItem(tripId, {
        day_number: newItem.day_number,
        time_slot: newItem.time_slot,
        place_name: newItem.place_name,
        category: newItem.category,
        notes: newItem.notes,
      }),
    onSuccess: async () => {
      setNewItem({
        id: 0,
        day_number: 1,
        time_slot: "morning",
        place_name: "",
        category: "관광",
        notes: "",
      });
      await queryClient.invalidateQueries({ queryKey: queryKeys.trip(tripId) });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (item: EditableItineraryItem) =>
      updateItineraryItem(tripId, item.id, {
        day_number: item.day_number,
        time_slot: item.time_slot,
        place_name: item.place_name,
        category: item.category,
        notes: item.notes,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.trip(tripId) });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (itemId: number) => deleteItineraryItem(tripId, itemId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.trip(tripId) });
    },
  });

  if (!tripDetail || !budget) {
    return (
      <AppShell>
        <div className="card">
          <h2 className="section-title">여행 정보를 불러오는 중입니다.</h2>
          <p className="section-subtitle">실제 저장된 일정과 기록 관리 화면을 준비하고 있어요.</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <TripHeader trip={tripDetail.overview} />
      <div className="row" style={{ marginBottom: 16, justifyContent: "flex-end" }}>
        <Link className="admin-primary-link" to={`/trips/${tripId}/memory`}>
          여행 기록 관리로 이동
        </Link>
      </div>

      <div className="page-grid grid-two">
        <div className="stack">
          <WeatherBanner />
          <TripSummary
            budgetLabel={tripDetail.overview.budgetLabel}
            companionLabel={tripDetail.overview.companionLabel}
            weatherSummary={tripDetail.overview.weatherSummary}
          />
        </div>
        <div className="stack">
          <BudgetSummaryCard budget={budget} />
          <ExpenseList expenses={expenses} />
          <ShareLinkModal />
        </div>
      </div>

      <section className="card card-tinted stack" style={{ marginTop: 20 }}>
        <div className="section-header">
          <div>
            <span className="section-kicker">ITINERARY EDITOR</span>
            <h2 className="section-title">여행 일정 수정</h2>
            <p className="section-subtitle">
              규칙기반으로 만든 일정이든 직접 만든 일정이든, 여기서 바로 수정하고 새 일정을 추가할 수 있어요.
            </p>
          </div>
        </div>

        <div className="stack">
          {Object.keys(itineraryByDay)
            .map(Number)
            .sort((left, right) => left - right)
            .map((dayNumber) => (
              <article key={dayNumber} className="planner-day-card">
                <div className="planner-day-header">
                  <div>
                    <span className="planner-day-label">DAY {dayNumber}</span>
                    <strong className="trip-card-title">{dayNumber}일차 일정</strong>
                  </div>
                </div>

                <div className="stack">
                  {itineraryByDay[dayNumber].map((item) => (
                    <div key={item.id} className="timeline-item community-entry-card stack">
                      <div className="community-inline-grid">
                        <label className="field">
                          <span>일차</span>
                          <input
                            min="1"
                            type="number"
                            value={item.day_number}
                            onChange={(event) =>
                              setEditableItems((prev) =>
                                prev.map((current) =>
                                  current.id === item.id
                                    ? { ...current, day_number: Number(event.target.value) || 1 }
                                    : current,
                                ),
                              )
                            }
                          />
                        </label>
                        <label className="field">
                          <span>시간대</span>
                          <select
                            value={item.time_slot}
                            onChange={(event) =>
                              setEditableItems((prev) =>
                                prev.map((current) =>
                                  current.id === item.id ? { ...current, time_slot: event.target.value } : current,
                                ),
                              )
                            }
                          >
                            {timeSlotOptions.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>

                      <div className="community-inline-grid">
                        <label className="field">
                          <span>장소 이름</span>
                          <input
                            value={item.place_name}
                            onChange={(event) =>
                              setEditableItems((prev) =>
                                prev.map((current) =>
                                  current.id === item.id ? { ...current, place_name: event.target.value } : current,
                                ),
                              )
                            }
                          />
                        </label>
                        <label className="field">
                          <span>카테고리</span>
                          <input
                            list="itinerary-category-options"
                            value={item.category}
                            onChange={(event) =>
                              setEditableItems((prev) =>
                                prev.map((current) =>
                                  current.id === item.id ? { ...current, category: event.target.value } : current,
                                ),
                              )
                            }
                          />
                        </label>
                      </div>

                      <label className="field">
                        <span>메모</span>
                        <textarea
                          rows={3}
                          value={item.notes}
                          onChange={(event) =>
                            setEditableItems((prev) =>
                              prev.map((current) =>
                                current.id === item.id ? { ...current, notes: event.target.value } : current,
                              ),
                            )
                          }
                        />
                      </label>

                      <div className="row">
                        <button
                          className="button primary"
                          disabled={updateMutation.isPending}
                          type="button"
                          onClick={() => updateMutation.mutate(item)}
                        >
                          저장
                        </button>
                        <button
                          className="button secondary"
                          disabled={deleteMutation.isPending}
                          type="button"
                          onClick={() => deleteMutation.mutate(item.id)}
                        >
                          삭제
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            ))}

          {!editableItems.length ? (
            <div className="admin-empty-card">
              <strong>아직 저장된 일정이 없어요.</strong>
              <p>아래에서 새 일정을 직접 추가하면 사용자가 직접 만드는 여행 일정으로 시작할 수 있습니다.</p>
            </div>
          ) : null}
        </div>

        <datalist id="itinerary-category-options">
          {categoryOptions.map((option) => (
            <option key={option} value={option} />
          ))}
        </datalist>

        <section className="card stack">
          <div>
            <h3 className="section-title">새 일정 추가</h3>
            <p className="section-subtitle">직접 새 장소를 넣어서 여행 일정을 손으로 완성할 수 있어요.</p>
          </div>
          <div className="community-inline-grid">
            <label className="field">
              <span>일차</span>
              <input
                min="1"
                type="number"
                value={newItem.day_number}
                onChange={(event) => setNewItem((prev) => ({ ...prev, day_number: Number(event.target.value) || 1 }))}
              />
            </label>
            <label className="field">
              <span>시간대</span>
              <select
                value={newItem.time_slot}
                onChange={(event) => setNewItem((prev) => ({ ...prev, time_slot: event.target.value }))}
              >
                {timeSlotOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="community-inline-grid">
            <label className="field">
              <span>장소 이름</span>
              <input
                value={newItem.place_name}
                onChange={(event) => setNewItem((prev) => ({ ...prev, place_name: event.target.value }))}
              />
            </label>
            <label className="field">
              <span>카테고리</span>
              <input
                list="itinerary-category-options"
                value={newItem.category}
                onChange={(event) => setNewItem((prev) => ({ ...prev, category: event.target.value }))}
              />
            </label>
          </div>
          <label className="field">
            <span>메모</span>
            <textarea
              rows={4}
              value={newItem.notes}
              onChange={(event) => setNewItem((prev) => ({ ...prev, notes: event.target.value }))}
            />
          </label>
          <button
            className="button primary"
            disabled={createMutation.isPending || !newItem.place_name.trim()}
            onClick={() => createMutation.mutate()}
            type="button"
          >
            {createMutation.isPending ? "추가 중..." : "새 일정 추가"}
          </button>
        </section>
      </section>

      <div className="stack" style={{ marginTop: 20 }}>
        <ReportSummary report={mockReportOverview} />
        <ReportInsights insights={mockReportOverview.insights} />
      </div>
    </AppShell>
  );
}
