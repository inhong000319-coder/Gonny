import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../providers/auth-provider";
import { Button } from "../../shared/components/ui/button";

const navItems = [
  { to: "/", label: "홈" },
  { to: "/trips", label: "내 여행" },
  { to: "/inspiration", label: "탐색" },
  { to: "/community", label: "커뮤니티" },
];

export function SiteHeader() {
  const location = useLocation();
  const { isAuthenticated, user } = useAuth();
  const profileInitial = user?.nickname?.slice(0, 1).toUpperCase() ?? "G";

  return (
    <header className="topbar">
      <div className="topbar-brand-group">
        <Link className="brand" to="/">Gonny</Link>
      </div>
      <nav className="nav">
        {navItems.map((item) => (
          <Link
            className={(item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to)) ? "nav-link active" : "nav-link"}
            key={item.to}
            to={item.to}
          >
            {item.label}
          </Link>
        ))}
        {isAuthenticated ? (
          <Link aria-label="프로필로 이동" className="topbar-profile" to="/profile">
            <span className="topbar-profile-avatar">{profileInitial}</span>
            <span>{user?.nickname ?? "프로필"}</span>
          </Link>
        ) : (
          <Link to="/login"><Button className="topbar-cta">로그인</Button></Link>
        )}
      </nav>
    </header>
  );
}
