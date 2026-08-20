import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { updateTripFavorite } from "../../features/trips/api/update-trip-favorite";
import { TripList } from "../../features/trips/components/trip-list";
import { useTripsQuery } from "../../features/trips/hooks/use-trips-query";
import { queryKeys } from "../../shared/api/query-keys";
import { Button } from "../../shared/components/ui/button";

export function TripsPage() {
  const queryClient = useQueryClient();
  const { data: trips = [] } = useTripsQuery();
  const favoriteCount = trips.filter((trip) => trip.isFavorite).length;
  const completedCount = trips.filter((trip) => trip.status === "completed").length;
  const favoriteMutation = useMutation({
    mutationFn: ({ tripId, isFavorite }: { tripId: string; isFavorite: boolean }) => updateTripFavorite(tripId, isFavorite),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: queryKeys.trips }),
  });

  return (
    <AppShell>
      <section className="trip-dashboard-hero">
        <div>
          <span className="travel-eyebrow">MY TRAVEL DESK</span>
          <h1>여행을 모아볼수록<br />다음 선택이 선명해져요.</h1>
          <p>계획 중인 일정부터 다시 꺼내 보고 싶은 여행 기록까지, 나만의 여행 아카이브를 한눈에 확인하세요.</p>
          <div className="travel-hero-actions">
            <Link to="/trips/new"><Button>새 여행 만들기</Button></Link>
            <Link to="/trips/recommend"><Button variant="secondary">맞춤 일정 추천</Button></Link>
          </div>
        </div>
        <div className="trip-dashboard-stats">
          <div><strong>{trips.length}</strong><span>전체 여행</span></div>
          <div><strong>{favoriteCount}</strong><span>다시 갈 여행</span></div>
          <div><strong>{completedCount}</strong><span>완료한 기록</span></div>
        </div>
      </section>
      {favoriteMutation.error ? <p className="form-error">즐겨찾기를 변경하지 못했습니다. 잠시 후 다시 시도해 주세요.</p> : null}
      <TripList
        pendingTripId={favoriteMutation.isPending ? (favoriteMutation.variables?.tripId ?? null) : null}
        trips={trips}
        onToggleFavorite={(tripId, nextFavorite) => favoriteMutation.mutate({ tripId, isFavorite: nextFavorite })}
      />
    </AppShell>
  );
}
