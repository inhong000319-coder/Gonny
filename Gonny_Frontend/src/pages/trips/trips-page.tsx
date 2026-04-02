import { Link } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { TripList } from "../../features/trips/components/trip-list";
import { useTripsQuery } from "../../features/trips/hooks/use-trips-query";
import { Button } from "../../shared/components/ui/button";

export function TripsPage() {
  const { data: trips = [] } = useTripsQuery();

  return (
    <AppShell>
      <section className="page-hero panel">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h1 className="section-title" style={{ fontSize: "2rem", margin: 0 }}>
              내 여행
            </h1>
            <p className="section-subtitle" style={{ margin: "8px 0 0" }}>
              생성한 일정과 진행 중인 여행을 한 곳에서 관리해보세요.
            </p>
          </div>
          <Link to="/trips/new">
            <Button>새 여행 만들기</Button>
          </Link>
        </div>
      </section>
      <TripList trips={trips} />
    </AppShell>
  );
}
