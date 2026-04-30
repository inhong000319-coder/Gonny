import { FormEvent, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { useCreateTripTodoMutation } from "../../features/community/hooks/use-create-trip-todo-mutation";
import { useTripCommunityQuery } from "../../features/community/hooks/use-trip-community-query";
import { useUpdateTripTodoMutation } from "../../features/community/hooks/use-update-trip-todo-mutation";
import { useTripDetailQuery } from "../../features/trips/hooks/use-trip-detail-query";
import { Button } from "../../shared/components/ui/button";
import { ModalOverlay } from "../../shared/components/ui/modal-overlay";

const dayLabels = ["첫째 날", "둘째 날", "셋째 날", "넷째 날", "다섯째 날", "여섯째 날", "일곱째 날"];

export function TripMemoryPage() {
  const { tripId = "101" } = useParams();
  const { data: tripDetail } = useTripDetailQuery(tripId);
  const { data: community, isLoading } = useTripCommunityQuery(tripId);
  const createTripTodoMutation = useCreateTripTodoMutation(tripId);
  const updateTripTodoMutation = useUpdateTripTodoMutation(tripId);
  const [selectedDay, setSelectedDay] = useState(1);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [todoContent, setTodoContent] = useState("");

  const totalDays = useMemo(() => {
    const count = tripDetail?.dayPlans.length ?? 0;
    return count > 0 ? count : 1;
  }, [tripDetail]);

  const todos = community?.trip_todos ?? [];
  const todosForSelectedDay = todos.filter((todo) => todo.day_number === selectedDay);
  const doneCount = todosForSelectedDay.filter((todo) => todo.is_done).length;

  const handleCreateTodo = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!todoContent.trim()) {
      return;
    }
    await createTripTodoMutation.mutateAsync({
      content: todoContent.trim(),
      day_number: selectedDay,
      is_done: false,
    });
    setTodoContent("");
    setIsCreateModalOpen(false);
  };

  if (!tripDetail) {
    return (
      <AppShell>
        <div className="card">
          <h2 className="section-title">기록 관리 화면을 준비하고 있어요.</h2>
          <p className="section-subtitle">잠시만 기다리면 해당 여행의 기록 메뉴를 불러옵니다.</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <section className="page-hero panel panel-gradient">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <span className="section-kicker">TRAVEL MEMORY</span>
            <h1 className="section-title" style={{ fontSize: "2.2rem", margin: "8px 0" }}>
              {tripDetail.overview.title} 기록 관리
            </h1>
            <p className="section-subtitle" style={{ marginBottom: 0 }}>
              여행 다이어리와 장소 평가는 상단에서 바로 이동하고, TODO 리스트는 이 메인 화면에서 바로 관리할 수 있어요.
            </p>
          </div>
          <div className="row">
            <Link to={`/trips/${tripId}`}>
              <Button variant="secondary">여행 상세로 돌아가기</Button>
            </Link>
          </div>
        </div>
      </section>

      <section className="memory-hub-shell">
        <div className="memory-hub-nav">
          <Link to={`/trips/${tripId}/memory/diary`}>
            <Button className="memory-hub-button" variant="secondary">
              여행 다이어리
            </Button>
          </Link>
          <Link to={`/trips/${tripId}/memory/reviews`}>
            <Button className="memory-hub-button" variant="secondary">
              장소 평가
            </Button>
          </Link>
        </div>

        <section className="card card-tinted stack">
          <div className="section-header">
            <div>
              <h2 className="section-title">여행 준비 TODO</h2>
              <p className="section-subtitle">
                {tripDetail.overview.destination} · {tripDetail.overview.dateRangeLabel}
              </p>
            </div>
            <div className="row">
              <Button onClick={() => setIsCreateModalOpen(true)} variant="secondary">
                리스트 추가하기
              </Button>
              <div className="chip-list">
              <span className="chip">전체 {todos.length}개</span>
              <span className="chip">선택한 날짜 완료 {doneCount} / {todosForSelectedDay.length}</span>
              </div>
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
            <strong>{dayLabels[selectedDay - 1] ?? `${selectedDay}일차`} TODO</strong>
            <span>완료 {doneCount} / 전체 {todosForSelectedDay.length}</span>
          </div>

          {isLoading ? <p className="section-subtitle">TODO 목록을 불러오고 있어요.</p> : null}

          <div className="memory-scroll-list">
            {todosForSelectedDay.map((todo) => (
              <article key={todo.id} className="timeline-item community-entry-card memory-list-card">
                <div className="memory-todo-row">
                  <label className="memory-todo-check">
                    <input
                      checked={todo.is_done}
                      disabled={updateTripTodoMutation.isPending}
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
                  <span className="chip">{todo.is_done ? "완료" : "진행 중"}</span>
                </div>
              </article>
            ))}

            {!isLoading && !todosForSelectedDay.length ? (
              <div className="admin-empty-card">
                <strong>이 날짜에는 아직 TODO가 없어요.</strong>
                <p>리스트 추가하기 버튼으로 준비해야 할 일과 먹고 싶은 것들을 날짜별로 바로 추가해보세요.</p>
              </div>
            ) : null}
          </div>
        </section>
      </section>

      {isCreateModalOpen ? (
        <ModalOverlay className="memory-modal" onClose={() => setIsCreateModalOpen(false)}>
          <div className="section-header">
            <div>
              <h2 className="section-title">TODO 리스트 추가</h2>
              <p className="section-subtitle">현재 보고 있는 날짜에 해야 할 일을 바로 추가해보세요.</p>
            </div>
            <button className="button ghost" onClick={() => setIsCreateModalOpen(false)} type="button">
              닫기
            </button>
          </div>

          <form className="stack" onSubmit={handleCreateTodo}>
            <div className="memory-summary-strip">
              <strong>{dayLabels[selectedDay - 1] ?? `${selectedDay}일차`} 기록</strong>
              <span>
                {tripDetail.overview.destination} · {tripDetail.overview.dateRangeLabel}
              </span>
            </div>
            <label className="field">
              <span>할 일</span>
              <input
                required
                className="input"
                placeholder="예: 흑돼지 먹기, 늦지 않게 공항 가기"
                value={todoContent}
                onChange={(event) => setTodoContent(event.target.value)}
              />
            </label>
            <div className="row">
              <button className="button secondary" onClick={() => setIsCreateModalOpen(false)} type="button">
                취소
              </button>
              <Button disabled={createTripTodoMutation.isPending} type="submit">
                {createTripTodoMutation.isPending ? "추가 중.." : "TODO 저장"}
              </Button>
            </div>
          </form>
        </ModalOverlay>
      ) : null}
    </AppShell>
  );
}
