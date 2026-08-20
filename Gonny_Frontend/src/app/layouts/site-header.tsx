import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../providers/auth-provider";
import { Button } from "../../shared/components/ui/button";

const navItems = [
  { to: "/", label: "Home" },
  { to: "/trips", label: "My Trips" },
  { to: "/inspiration", label: "Explore" },
  { to: "/community", label: "Community" },
];

export function SiteHeader() {
  const location = useLocation();
  const { isAuthenticated, user } = useAuth();
  const profileInitial = user?.nickname?.slice(0, 1).toUpperCase() ?? "G";

  return (
    <header className="topbar">
      <div className="topbar-brand-group">
        <Link className="brand" to="/">Gonny</Link>
        <span className="topbar-tag">travel, together</span>
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
            <span>{user?.nickname ?? "Profile"}</span>
          </Link>
        ) : (
          <Link to="/login"><Button className="topbar-cta">Login</Button></Link>
        )}
      </nav>
    </header>
  );
}
