import { Link } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { useAuth } from "../../app/providers/auth-provider";
import { useMeQuery } from "../../features/auth/hooks/use-me-query";
import { useTripsQuery } from "../../features/trips/hooks/use-trips-query";
import { Button } from "../../shared/components/ui/button";

export function ProfilePage() {
  const { user, signOut, isAuthenticated } = useAuth();
  const { data } = useMeQuery(isAuthenticated);
  const { data: trips = [] } = useTripsQuery();
  const profile = data ?? user;
  const favoriteTrips = trips.filter((trip) => trip.isFavorite).slice(0, 3);
  const initial = profile?.nickname?.slice(0, 1).toUpperCase() ?? "G";

  return (
    <AppShell>
      <section className="profile-travel-hero">
        <div className="profile-avatar-large">{initial}</div>
        <div className="profile-travel-copy">
          <span className="travel-eyebrow">TRAVEL ID</span>
          <h1>{profile?.nickname ?? "Gonny traveler"}의 여행 지도</h1>
          <p>{profile?.email ?? "여행을 기록하고 다음 여행자를 위한 힌트를 남겨 보세요."}</p>
        </div>
        <div className="profile-hero-actions">
          <Link to="/trips"><Button variant="secondary">내 여행 보기</Button></Link>
          <Button onClick={signOut} variant="ghost">로그아웃</Button>
        </div>
      </section>

      <section className="profile-overview-grid">
        <article className="profile-overview-card"><span>ARCHIVED TRIPS</span><strong>{trips.length}</strong><p>차곡차곡 모인 여행</p></article>
        <article className="profile-overview-card warm"><span>FAVORITES</span><strong>{favoriteTrips.length}</strong><p>다시 떠나고 싶은 곳</p></article>
        <article className="profile-overview-card mint"><span>NEXT STEP</span><strong>+</strong><p>다음 여행을 계획해 보세요</p></article>
      </section>

      <section className="profile-memory-section">
        <div className="section-heading-inline">
          <div><span className="travel-eyebrow">SAVED FOR LATER</span><h2>다시 펼쳐 보고 싶은 여행</h2></div>
          <Link to="/trips" className="text-link">전체 여행 보기</Link>
        </div>
        {!favoriteTrips.length ? (
          <div className="profile-empty-state">
            <strong>아직 저장한 여행이 없어요.</strong>
            <p>여행 목록에서 마음에 드는 일정을 저장하면 이곳에 모아둘 수 있어요.</p>
            <Link to="/trips"><Button>여행 둘러보기</Button></Link>
          </div>
        ) : (
          <div className="profile-memory-grid">
            {favoriteTrips.map((trip) => (
              <Link className="profile-memory-card" key={trip.id} to={`/trips/${trip.id}`}>
                <span>{trip.destination}</span>
                <h3>{trip.title}</h3>
                <p>{trip.startDate} - {trip.endDate}</p>
                <small>여행 상세 보기 ↗</small>
              </Link>
            ))}
          </div>
        )}
      </section>
    </AppShell>
  );
}
