import { PropsWithChildren } from "react";
import { SiteFooter } from "./site-footer";
import { SiteHeader } from "./site-header";

export function AuthLayout({ children }: PropsWithChildren) {
  return (
    <div className="site-shell">
      <SiteHeader />
      <main className="auth-layout">
        <div className="auth-card">{children}</div>
      </main>
      <SiteFooter />
    </div>
  );
}
