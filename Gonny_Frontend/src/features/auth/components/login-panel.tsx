import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../../app/providers/auth-provider";
import { Button } from "../../../shared/components/ui/button";
import { SocialLoginButton } from "./social-login-button";
import "./login-panel.css";

export function LoginPanel() {
  const navigate = useNavigate();
  const location = useLocation();
  const { signInDemo } = useAuth();
  const returnTo = (location.state as { from?: string } | null)?.from ?? "/";

  const handleLogin = () => {
    signInDemo();
    navigate(returnTo, { replace: true });
  };

  return (
    <div className="auth-hero">
      <Button className="auth-back-button" onClick={() => navigate(-1)} variant="ghost">
        ← 이전 화면으로
      </Button>
      <div className="auth-copy">
        <h1 className="auth-title">로그인하고 다음 여행을 바로 이어서 준비해보세요.</h1>
        <p className="auth-description">
          인증 화면도 메인과 같은 밝은 톤으로 맞춰두었습니다. 소셜 로그인을 통해 내 여행
          기록, 공유 일정, 예산과 회고 정보까지 자연스럽게 이어집니다.
        </p>
        <div className="chip-list">
          <span className="chip">내 여행 기록</span>
          <span className="chip">공유 일정 확인</span>
          <span className="chip">예산 · 회고 동기화</span>
        </div>
      </div>

      <div className="card stack">
        <h2 className="section-title" style={{ fontSize: "1.6rem", margin: 0 }}>
          소셜 로그인으로 계속하기
        </h2>
        <p className="section-subtitle" style={{ marginBottom: 8 }}>
          현재는 데모 인증 흐름으로 연결되어 있지만, 화면은 실제 서비스처럼 보이도록
          정리해두었습니다.
        </p>
        <SocialLoginButton provider="kakao" onClick={handleLogin} />
        <SocialLoginButton provider="google" onClick={handleLogin} />
      </div>
    </div>
  );
}
