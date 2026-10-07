import { PropsWithChildren } from "react";
import { SiteFooter } from "./site-footer";
import { SiteHeader } from "./site-header";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="site-shell">
      <SiteHeader />
      <main className="page-container">{children}</main>
      <SiteFooter />
    </div>
  );
}
