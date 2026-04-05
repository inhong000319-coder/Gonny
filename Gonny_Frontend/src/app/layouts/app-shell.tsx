import { PropsWithChildren } from "react";
import { Link, useLocation } from "react-router-dom";

const navItems = [
  { to: "/trips", label: "여행" },
  { to: "/inspiration", label: "영감" },
  { to: "/admin/data", label: "데이터 관리" },
  { to: "/profile", label: "프로필" },
];

export function AppShell({ children }: PropsWithChildren) {
  const location = useLocation();

  return (
    <div>
      <header className="topbar">
        <Link className="brand" to="/trips">
          Gonny
        </Link>
        <nav className="nav">
          {navItems.map((item) => (
            <Link
              key={item.to}
              className={location.pathname.startsWith(item.to) ? "nav-link active" : "nav-link"}
              to={item.to}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </header>

      <main className="page-container">{children}</main>
    </div>
  );
}
