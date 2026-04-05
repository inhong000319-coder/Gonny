import { PropsWithChildren } from "react";
import { Link } from "react-router-dom";

export function PublicLayout({ children }: PropsWithChildren) {
  return (
    <div>
      <header className="topbar">
        <Link className="brand" to="/">
          Gonny
        </Link>
        <nav className="nav">
          <Link className="nav-link" to="/planner">
            플래너
          </Link>
          <Link className="nav-link" to="/admin/data">
            데이터 관리
          </Link>
          <Link className="nav-link" to="/login">
            로그인
          </Link>
        </nav>
      </header>
      <main className="page-container">{children}</main>
    </div>
  );
}
