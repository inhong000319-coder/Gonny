import { PropsWithChildren } from "react";
import { Link } from "react-router-dom";

export function PublicLayout({ children }: PropsWithChildren) {
  return (
    <div>
      <header className="topbar">
        <Link className="brand" to="/">
          Gonny
        </Link>
        <Link className="nav-link" to="/login">
          로그인
        </Link>
      </header>
      <main className="page-container">{children}</main>
    </div>
  );
}
