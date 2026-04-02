import { PropsWithChildren } from "react";

export function AuthLayout({ children }: PropsWithChildren) {
  return (
    <div className="auth-layout">
      <div className="auth-card">{children}</div>
    </div>
  );
}
