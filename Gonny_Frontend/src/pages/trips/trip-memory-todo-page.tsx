import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { useCreateTripTodoMutation } from "../../features/community/hooks/use-create-trip-todo-mutation";
import { useTripCommunityQuery } from "../../features/community/hooks/use-trip-community-query";
import { useUpdateTripTodoMutation } from "../../features/community/hooks/use-update-trip-todo-mutation";
import { useTripDetailQuery } from "../../features/trips/hooks/use-trip-detail-query";
import { Button } from "../../shared/components/ui/button";
import { ModalOverlay } from "../../shared/components/ui/modal-overlay";

const dayLabels = ["첫째 날", "둘째 날", "셋째 날", "넷째 날", "다섯째 날", "여섯째 날", "일곱째 날"];

export function TripMemoryTodoPage() {
  const { tripId = "101" } = useParams();
  const { data: tripDetail } = useTripDetailQuery(tripId);
  const { data, isLoading } = useTripCommunityQuery(tripId);
  const createTripTodoMutation = useCreateTripTodoMutation(tripId);
  const updateTripTodoMutation = useUpdateTripTodoMutation(tripId);

  const [selectedDay, setSelectedDay] = useState(1);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [todoContent, setTodoContent] = useState("");
  const [todoDayNumber, setTodoDayNumber] = useState(1);

  const totalDays = useMemo(() => {
    const count = tripDetail?.dayPlans.length ?? 0;
    return count > 0 ? count : 1;
  }, [tripDetail]);

  useEffect(() => {
    setTodoDayNumber(selectedDay);
  }, [selectedDay]);

  const todos = data?.trip_todos ?? [];
  const todosForSelectedDay = todos.filter((todo) => todo.day_number === selectedDay);

  if (!tripDetail) {
    return (
      <AppShell>
        <div className="card">
          <h2 className="section-title">TODO 리스트 화면을 준비하고 있습니다.</h2>
        </div>
      </AppShell>
    );
  }

  const openCreateModal = () => {
    setTodoDayNumber(selectedDay);
    setTodoContent("");
    setIsCreateModalOpen(true);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await createTripTodoMutation.mutateAsync({
      content: todoContent.trim(),
      day_number: todoDayNumber,
      is_done: false,
    });
    setTodoContent("");
    setTodoDayNumber(selectedDay);
    setIsCreateModalOpen(false);
  };

  return (
    <AppShell>
      <section className="page-hero panel panel-gradient">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <span className="section-kicker">TRAVEL TODO</span>
            <h1 className="section-title" style={{ fontSize: "2.1rem", margin: "8px 0" }}>
              TODO 리스트
            </h1>
            <p className="section-subtitle" style={{ marginBottom: 0 }}>
              여행 전에 적어둔 할 일과 먹고 싶은 것, 챙길 것들을 날짜별로 나눠두고 하나씩 체크해보세요.
            </p>
          </div>
          <div className="row">
            <Button onClick={openCreateModal}>리스트 추가하기</Button>
            <Link to={`/trips/${tripId}/memory`}>
              <Button variant="secondary">기록 관리로 돌아가기</Button>
            </Link>
          </div>
        </div>
      </section>

      <section className="card stack">
        <div className="section-header">
          <div>
            <h2 className="section-title">{tripDetail.overview.title}</h2>
            <p className="section-subtitle">
              {tripDetail.overview.dateRangeLabel} · 현재 선택한 날짜의 TODO만 모아서 보고 체크할 수 있어요.
            </p>
          </div>
          <div className="chip-list">
            <span className="chip">전체 {todos.length}개</span>
            <span className="chip">완료 {todos.filter((todo) => todo.is_done).length}개</span>
          </div>
        </div>

        <div className="todo-day-pager">
          <button
            className="button secondary todo-nav-button"
            disabled={selectedDay === 1}
            onClick={() => setSelectedDay((value) => Math.max(1, value - 1))}
            type="button"
          >
            &lt;
          </button>
          {Array.from({ length: totalDays }, (_, index) => index + 1).map((dayNumber) => (
            <button
              key={dayNumber}
              className={`button ${selectedDay === dayNumber ? "primary" : "secondary"} todo-page-button`}
              onClick={() => setSelectedDay(dayNumber)}
              type="button"
            >
              {dayNumber}
            </button>
          ))}
          <button
            className="button secondary todo-nav-button"
            disabled={selectedDay === totalDays}
            onClick={() => setSelectedDay((value) => Math.min(totalDays, value + 1))}
            type="button"
          >
            &gt;
          </button>
        </div>

        <div className="memory-summary-strip">
          <strong>{dayLabels[selectedDay - 1] ?? `${selectedDay}일차`} 기록</strong>
          <span>
            완료 {todosForSelectedDay.filter((todo) => todo.is_done).length} / 전체 {todosForSelectedDay.length}
          </span>
        </div>

        {isLoading ? <p className="section-subtitle">TODO 목록을 불러오고 있습니다.</p> : null}

        <div className="memory-scroll-list">
          {todosForSelectedDay.map((todo) => (
            <article key={todo.id} className="timeline-item community-entry-card memory-list-card">
              <div className="memory-todo-row">
                <label className="memory-todo-check">
                  <input
                    checked={todo.is_done}
                    onChange={() =>
                      updateTripTodoMutation.mutate({
                        todoId: todo.id,
                        payload: { is_done: !todo.is_done },
                      })
                    }
                    type="checkbox"
                  />
                  <span className={todo.is_done ? "memory-todo-text done" : "memory-todo-text"}>{todo.content}</span>
                </label>
                <span className="chip">{todo.is_done ? "완료" : "진행 전"}</span>
              </div>
            </article>
          ))}

          {!isLoading && !todosForSelectedDay.length ? (
            <div className="admin-empty-card">
              <strong>이 날짜에는 아직 TODO가 없어요.</strong>
              <p>리스트 추가하기 버튼으로 이 날에 꼭 하고 싶은 일이나 챙길 일을 먼저 적어두세요.</p>
            </div>
          ) : null}
        </div>
      </section>

      {isCreateModalOpen ? (
        <ModalOverlay className="memory-modal" onClose={() => setIsCreateModalOpen(false)}>
            <div className="section-header">
              <div>
                <h2 className="section-title">TODO 리스트 추가</h2>
                <p className="section-subtitle">원하는 날짜를 고르고 할 일을 하나씩 적어두세요.</p>
              </div>
              <button className="button ghost" onClick={() => setIsCreateModalOpen(false)} type="button">
                닫기
              </button>
            </div>

            <form className="stack" onSubmit={handleSubmit}>
              <label className="field">
                <span>날짜 선택</span>
                <select value={String(todoDayNumber)} onChange={(event) => setTodoDayNumber(Number(event.target.value))}>
                  {Array.from({ length: totalDays }, (_, index) => index + 1).map((dayNumber) => (
                    <option key={dayNumber} value={dayNumber}>
                      {dayLabels[dayNumber - 1] ?? `${dayNumber}일차`}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>할 일</span>
                <input
                  required
                  value={todoContent}
                  onChange={(event) => setTodoContent(event.target.value)}
                  placeholder="예: 흑돼지 먹기, 용머리해안 가기"
                />
              </label>
              <Button disabled={createTripTodoMutation.isPending} type="submit">
                {createTripTodoMutation.isPending ? "추가 중..." : "TODO 저장"}
              </Button>
            </form>
        </ModalOverlay>
      ) : null}
    </AppShell>
  );
}
