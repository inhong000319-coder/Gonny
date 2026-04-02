import { useNavigate } from "react-router-dom";
import { useAuth } from "../../../app/providers/auth-provider";
import { SocialLoginButton } from "./social-login-button";

function SparkIcon() {
  return (
    <svg aria-hidden="true" className="landing-mini-icon" viewBox="0 0 24 24">
      <path
        d="M12 2.5l1.95 5.55L19.5 10l-5.55 1.95L12 17.5l-1.95-5.55L4.5 10l5.55-1.95L12 2.5Zm6.25 12 1 2.75L22 18.25l-2.75 1-1 2.75-1-2.75-2.75-1 2.75-1 1-2.75Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function LoginPanel() {
  const navigate = useNavigate();
  const { signInDemo } = useAuth();

  const handleLogin = () => {
    signInDemo();
    navigate("/trips");
  };

  return (
    <div className="auth-hero">
      <div className="auth-copy">
        <div className="landing-pill">
          <SparkIcon />
          <span>빠른 시작</span>
        </div>
        <h1 className="auth-title">로그인하고 다음 여행을 바로 이어서 준비해보세요.</h1>
        <p className="auth-description">
          인증 화면도 메인과 같은 밝은 톤으로 맞춰두었습니다. 소셜 로그인을 통해 내 여행
          기록, 공유 일정, 예산과 회고 정보까지 자연스럽게 이어집니다.
        </p>
        <div className="auth-highlight-list">
          <div className="auth-highlight-item">내 여행 기록</div>
          <div className="auth-highlight-item">공유 일정 확인</div>
          <div className="auth-highlight-item">예산 · 회고 동기화</div>
        </div>
      </div>

      <div className="auth-login-box">
        <div className="stack">
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
    </div>
  );
}
