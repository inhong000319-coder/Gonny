import { Button } from "../../../shared/components/ui/button";

type SocialLoginButtonProps = {
  provider: "kakao" | "google";
  onClick: () => void;
};

function KakaoIcon() {
  return (
    <svg
      aria-hidden="true"
      className="social-login-icon"
      fill="none"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect fill="#FEE500" height="24" rx="12" width="24" />
      <path
        d="M12 6.3c-3.33 0-6.03 2.06-6.03 4.6 0 1.66 1.16 3.11 2.9 3.92l-.73 2.68c-.06.22.19.4.38.27l3.13-2.08c.18.01.23.02.35.02 3.33 0 6.03-2.06 6.03-4.81 0-2.52-2.7-4.6-6.03-4.6Z"
        fill="#191600"
      />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg
      aria-hidden="true"
      className="social-login-icon"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="12" cy="12" fill="white" r="12" />
      <path
        d="M19.64 12.2c0-.57-.05-1.11-.15-1.64H12v3.1h4.27a3.64 3.64 0 0 1-1.58 2.39v1.98h2.56c1.5-1.38 2.39-3.41 2.39-5.83Z"
        fill="#4285F4"
      />
      <path
        d="M12 20c2.16 0 3.97-.72 5.29-1.97l-2.56-1.98c-.71.48-1.62.77-2.73.77-2.1 0-3.88-1.41-4.52-3.31H4.84v2.04A7.99 7.99 0 0 0 12 20Z"
        fill="#34A853"
      />
      <path
        d="M7.48 13.51A4.8 4.8 0 0 1 7.23 12c0-.52.09-1.02.25-1.51V8.45H4.84A8 8 0 0 0 4 12c0 1.28.31 2.49.84 3.55l2.64-2.04Z"
        fill="#FBBC05"
      />
      <path
        d="M12 7.18c1.18 0 2.24.41 3.08 1.2l2.31-2.31C15.96 4.76 14.16 4 12 4a8 8 0 0 0-7.16 4.45l2.64 2.04c.64-1.9 2.42-3.31 4.52-3.31Z"
        fill="#EA4335"
      />
    </svg>
  );
}

export function SocialLoginButton({ provider, onClick }: SocialLoginButtonProps) {
  const isKakao = provider === "kakao";
  const label = isKakao ? "카카오로 시작하기" : "구글로 시작하기";
  const variant = isKakao ? "primary" : "secondary";
  const icon = isKakao ? <KakaoIcon /> : <GoogleIcon />;

  return (
    <Button className="social-login-button" onClick={onClick} variant={variant}>
      {icon}
      <span>{label}</span>
    </Button>
  );
}
