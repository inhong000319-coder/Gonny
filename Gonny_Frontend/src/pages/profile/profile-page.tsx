import { Link } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { useAuth } from "../../app/providers/auth-provider";
import { useMeQuery } from "../../features/auth/hooks/use-me-query";
import { useTripsQuery } from "../../features/trips/hooks/use-trips-query";
import { Button } from "../../shared/components/ui/button";

function UserIcon() {
  return (
    <svg aria-hidden="true" className="landing-feature-icon" fill="none" viewBox="0 0 24 24">
      <circle cx="12" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.8" />
      <path d="M5.5 19c1.2-3 3.6-4.5 6.5-4.5s5.3 1.5 6.5 4.5" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function MailIcon() {
  return (
    <svg aria-hidden="true" className="landing-feature-icon" fill="none" viewBox="0 0 24 24">
      <rect height="12" rx="3" stroke="currentColor" strokeWidth="1.8" width="16" x="4" y="6" />
      <path d="m6 8 6 4 6-4" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

export function ProfilePage() {
  const { user, signOut, isAuthenticated } = useAuth();
  const { data } = useMeQuery(isAuthenticated);
  const { data: trips = [] } = useTripsQuery();
  const profile = data ?? user;
  const favoriteTrips = trips.filter((trip) => trip.isFavorite).slice(0, 3);

  return (
    <AppShell>
      <section className="page-hero panel panel-gradient">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <span className="section-kicker">MY ACCOUNT</span>
            <h1 className="section-title" style={{ fontSize: "2.2rem", margin: "8px 0" }}>
              프로필
            </h1>
            <p className="section-subtitle" style={{ marginBottom: 0 }}>
              내 계정 정보와 자주 꺼내보는 여행 일정을 한 곳에서 확인할 수 있어요.
            </p>
          </div>
          <div className="landing-feature-icon-wrap">
            <UserIcon />
          </div>
        </div>
      </section>

      <div className="stack">
        <div className="card card-tinted stack">
          <div className="profile-info-card">
            <div className="profile-info-icon">
              <UserIcon />
            </div>
            <div>
              <strong className="profile-info-label">닉네임</strong>
              <p className="profile-info-value">{profile?.nickname}</p>
            </div>
          </div>

          <div className="profile-info-card">
            <div className="profile-info-icon">
              <MailIcon />
            </div>
            <div>
              <strong className="profile-info-label">이메일</strong>
              <p className="profile-info-value">{profile?.email}</p>
            </div>
          </div>

          <div className="row">
            <Button variant="secondary">프로필 수정</Button>
            <Button onClick={signOut} variant="ghost">
              로그아웃
            </Button>
          </div>
        </div>

        <section className="card card-tinted profile-shortcut-card">
          <div className="section-header">
            <div>
              <span className="section-kicker">TRAVEL MEMORY</span>
              <h2 className="section-title">여행 기록 바로가기</h2>
              <p className="section-subtitle">
                전체 여행 보기에서 즐겨찾기로 등록한 일정 최대 3개를 여기에서 바로 확인할 수 있어요.
              </p>
            </div>
            <Link to="/trips">
              <Button variant="secondary">전체 여행 보기</Button>
            </Link>
          </div>

          {!favoriteTrips.length ? (
            <div className="admin-empty-card">
              <strong>아직 즐겨찾기한 여행이 없어요.</strong>
              <p>전체 여행 보기에서 자주 꺼내볼 여행을 즐겨찾기로 등록하면 이곳에 바로 보여드릴게요.</p>
            </div>
          ) : (
            <div className="profile-trip-grid">
              {favoriteTrips.map((trip) => (
                <article key={trip.id} className="trip-card trip-card-polished profile-trip-card">
                  <div className="stack" style={{ gap: 10 }}>
                    <strong className="trip-card-title">{trip.title}</strong>
                    <p className="section-subtitle" style={{ margin: 0 }}>
                      {trip.destination} · {trip.startDate} - {trip.endDate}
                    </p>
                    <div className="trip-card-meta">
                      <span>예산 {trip.budget.toLocaleString()}원</span>
                      <span>동행 {trip.companionCount}명</span>
                      <span>즐겨찾기 일정</span>
                    </div>
                    <div className="row">
                      <Link to={`/trips/${trip.id}`}>
                        <Button variant="secondary">여행 상세 보기</Button>
                      </Link>
                      <Link to={`/trips/${trip.id}/memory`}>
                        <Button>기록 관리로 이동</Button>
                      </Link>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
