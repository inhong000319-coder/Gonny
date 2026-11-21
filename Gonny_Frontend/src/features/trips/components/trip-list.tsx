import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { TripCard } from "./trip-card";
import { TripSummaryItem } from "../../../shared/types/domain";
import { Button } from "../../../shared/components/ui/button";
import { EmptyState } from "../../../shared/components/feedback/empty-state";

type TripListProps = {
  trips: TripSummaryItem[];
  onToggleFavorite: (tripId: string, nextFavorite: boolean) => void;
  pendingTripId?: string | null;
};

const pageSize = 5;

export function TripList({ trips, onToggleFavorite, pendingTripId }: TripListProps) {
  const [keyword, setKeyword] = useState("");
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [page, setPage] = useState(1);
  const filteredTrips = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLocaleLowerCase();
    return trips.filter((trip) => {
      const matchesTitle = !normalizedKeyword || trip.title.toLocaleLowerCase().includes(normalizedKeyword);
      return matchesTitle && (!favoritesOnly || trip.isFavorite);
    });
  }, [favoritesOnly, keyword, trips]);
  const totalPages = Math.max(1, Math.ceil(filteredTrips.length / pageSize));
  const pagedTrips = filteredTrips.slice((page - 1) * pageSize, page * pageSize);

  useEffect(() => { setPage(1); }, [keyword, favoritesOnly]);
  useEffect(() => { if (page > totalPages) setPage(totalPages); }, [page, totalPages]);

  return (
    <section className="tl-section">
      <div className="tl-section-heading">
        <div><h2>내 여행 컬렉션</h2><p>최근 일정, 작성 중인 계획, 저장한 여행을 한곳에서 관리하세요.</p></div>
      </div>
      <div className="tl-toolbar">
        <label className="tl-search-field">
          <span>⌕</span>
          <input aria-label="여행 제목 검색" onChange={(event) => setKeyword(event.target.value)} placeholder="여행 제목으로 검색" value={keyword} />
        </label>
        <button className={favoritesOnly ? "tl-filter is-active" : "tl-filter"} onClick={() => setFavoritesOnly((current) => !current)} type="button">
          {favoritesOnly ? "★ 즐겨찾기만 보는 중" : "☆ 즐겨찾기만 보기"}
        </button>
      </div>
      {!trips.length ? (
        <EmptyState
          action={<Link to="/trips/recommend"><Button variant="secondary">새 여행 만들기</Button></Link>}
          description="첫 번째 여행을 만들면 이곳에 일정과 기록이 쌓입니다."
          title="아직 만든 여행이 없어요."
        />
      ) : !filteredTrips.length ? (
        <EmptyState
          action={
            <Button
              onClick={() => {
                setKeyword("");
                setFavoritesOnly(false);
              }}
              variant="secondary"
            >
              필터 초기화
            </Button>
          }
          description="다른 제목으로 검색하거나 즐겨찾기 필터를 해제해 보세요."
          title="조건에 맞는 여행이 없어요."
        />
      ) : (
        <>
          <div className="tl-list">{pagedTrips.map((trip) => <TripCard key={trip.id} pending={pendingTripId === trip.id} trip={trip} onToggleFavorite={onToggleFavorite} />)}</div>
          {totalPages > 1 ? <nav aria-label="여행 목록 페이지" className="tl-pagination">
            <button aria-label="이전 페이지" className="tl-page-button" disabled={page === 1} onClick={() => setPage((current) => current - 1)} type="button">←</button>
            {Array.from({ length: totalPages }, (_, index) => index + 1).map((pageNumber) => <button className={pageNumber === page ? "tl-page-button is-active" : "tl-page-button"} key={pageNumber} onClick={() => setPage(pageNumber)} type="button">{pageNumber}</button>)}
            <button aria-label="다음 페이지" className="tl-page-button" disabled={page === totalPages} onClick={() => setPage((current) => current + 1)} type="button">→</button>
          </nav> : null}
        </>
      )}
    </section>
  );
}
