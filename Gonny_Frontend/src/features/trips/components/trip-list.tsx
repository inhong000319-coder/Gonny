import { useEffect, useMemo, useState } from "react";
import { TripCard } from "./trip-card";
import { TripSummaryItem } from "../../../shared/types/domain";

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
    <section className="trip-archive-section">
      <div className="section-heading-inline">
        <div><span className="travel-eyebrow">PLANNER ARCHIVE</span><h2>내 여행 컬렉션</h2><p>최근 일정, 작성 중인 계획, 저장한 여행을 한곳에서 관리하세요.</p></div>
      </div>
      <div className="trip-collection-toolbar">
        <label className="trip-search-field">
          <span>⌕</span>
          <input aria-label="여행 제목 검색" onChange={(event) => setKeyword(event.target.value)} placeholder="여행 제목으로 검색" value={keyword} />
        </label>
        <button className={favoritesOnly ? "trip-filter active" : "trip-filter"} onClick={() => setFavoritesOnly((current) => !current)} type="button">
          {favoritesOnly ? "★ 즐겨찾기만 보는 중" : "☆ 즐겨찾기만 보기"}
        </button>
      </div>
      {!trips.length ? (
        <div className="profile-empty-state"><strong>아직 만든 여행이 없어요.</strong><p>첫 번째 여행을 만들면 이곳에 일정과 기록이 쌓입니다.</p></div>
      ) : !filteredTrips.length ? (
        <div className="profile-empty-state"><strong>조건에 맞는 여행이 없어요.</strong><p>다른 제목으로 검색하거나 즐겨찾기 필터를 해제해 보세요.</p></div>
      ) : (
        <>
          <div className="trip-list">{pagedTrips.map((trip) => <TripCard key={trip.id} pending={pendingTripId === trip.id} trip={trip} onToggleFavorite={onToggleFavorite} />)}</div>
          {totalPages > 1 ? <nav aria-label="여행 목록 페이지" className="trip-pagination">
            <button aria-label="이전 페이지" className="trip-page-button" disabled={page === 1} onClick={() => setPage((current) => current - 1)} type="button">←</button>
            {Array.from({ length: totalPages }, (_, index) => index + 1).map((pageNumber) => <button className={pageNumber === page ? "trip-page-button active" : "trip-page-button"} key={pageNumber} onClick={() => setPage(pageNumber)} type="button">{pageNumber}</button>)}
            <button aria-label="다음 페이지" className="trip-page-button" disabled={page === totalPages} onClick={() => setPage((current) => current + 1)} type="button">→</button>
          </nav> : null}
        </>
      )}
    </section>
  );
}
