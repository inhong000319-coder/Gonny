import { PropsWithChildren } from "react";
import { SiteHeader } from "./site-header";

export function PublicLayout({ children }: PropsWithChildren) {
  return (
    <div className="site-shell site-shell-public">
      <SiteHeader />
      <main className="page-container">{children}</main>
    </div>
  );
}
