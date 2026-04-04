import { AppShell } from "../../app/layouts/app-shell";
import { useAuth } from "../../app/providers/auth-provider";
import { useMeQuery } from "../../features/auth/hooks/use-me-query";
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
  const profile = data ?? user;

  return (
    <AppShell>
      <section className="page-hero panel panel-gradient">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <span className="section-kicker">My account</span>
            <h1 className="section-title" style={{ fontSize: "2.2rem", margin: "8px 0" }}>
              프로필
            </h1>
            <p className="section-subtitle" style={{ marginBottom: 0 }}>
              내 계정 정보와 기본 설정을 한눈에 볼 수 있는 화면입니다.
            </p>
          </div>
          <div className="landing-feature-icon-wrap">
            <UserIcon />
          </div>
        </div>
      </section>

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
    </AppShell>
  );
}
