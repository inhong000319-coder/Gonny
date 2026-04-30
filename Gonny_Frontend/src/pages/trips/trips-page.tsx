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
  const favoriteMutation = useMutation({
    mutationFn: ({ tripId, isFavorite }: { tripId: string; isFavorite: boolean }) => updateTripFavorite(tripId, isFavorite),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.trips });
    },
  });

  return (
    <AppShell>
      <section className="page-hero panel">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h1 className="section-title" style={{ fontSize: "2rem", margin: 0 }}>
              내 여행
            </h1>
            <p className="section-subtitle" style={{ margin: "8px 0 0" }}>
              생성한 여행과 추천받은 일정을 한곳에서 보고, 원하는 방식으로 새 여행을 시작해보세요.
            </p>
          </div>
          <div className="row">
            <Link to="/trips/new">
              <Button>새 여행 만들기</Button>
            </Link>
            <Link to="/trips/recommend">
              <Button variant="secondary">여행일정 추천받기</Button>
            </Link>
          </div>
        </div>
        {favoriteMutation.error ? (
          <p className="section-subtitle" style={{ margin: "12px 0 0", color: "#b42318" }}>
            {favoriteMutation.error instanceof Error ? favoriteMutation.error.message : "즐겨찾기 변경 중 문제가 생겼어요."}
          </p>
        ) : null}
      </section>
      <TripList
        pendingTripId={favoriteMutation.isPending ? ((favoriteMutation.variables?.tripId as string | undefined) ?? null) : null}
        trips={trips}
        onToggleFavorite={(tripId, nextFavorite) => favoriteMutation.mutate({ tripId, isFavorite: nextFavorite })}
      />
    </AppShell>
  );
}
