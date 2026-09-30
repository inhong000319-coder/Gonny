import { useEffect, useState } from "react";

import { RulePlanner } from "./features/rule-planner/RulePlanner";

const TEXT = {
  appKicker: "Gonny 프론트 워크스페이스",
  homeTitle: "Gonny 프론트 워크스페이스",
  homeDescription: "규칙기반 일정 생성기 페이지로 이동하세요.",
  plannerTitle: "규칙기반 일정 생성기",
  plannerDescription: "도시 데이터와 규칙만으로 단계별 여행 일정을 만드는 화면입니다.",
  home: "홈",
  rulePlanner: "규칙기반 일정생성",
  quickAccess: "페이지 바로가기",
  quickButtonPlanner: "규칙기반 일정생성기로 이동",
  freePlanner: "무료 일정 생성",
  plannerCardTitle: "규칙기반 일정생성기",
  plannerCardDescription:
    "대륙, 국가, 도시, 예산, 여행 컨셉, 여행 스타일을 단계별로 선택해 규칙기반 일정을 생성합니다.",
  openPlanner: "규칙기반 일정생성기 열기",
  homeCaption: "워크스페이스 시작",
  plannerCaption: "단계형 여행 플래너",
  quickPageShortcuts: "페이지 바로가기",
  featureNavigation: "기능 이동",
  ruleBasedTag: "규칙기반",
};

const ROUTES = {
  home: {
    path: "/",
    title: TEXT.homeTitle,
    description: TEXT.homeDescription,
  },
  rulePlanner: {
    path: "/rule-planner",
    title: TEXT.plannerTitle,
    description: TEXT.plannerDescription,
  },
};

function getCurrentPath() {
  return window.location.pathname || "/";
}

function navigate(path, setPathname) {
  window.history.pushState({}, "", path);
  setPathname(path);
}

function RouteShortcutList({ pathname, onNavigate }) {
  const items = [
    { label: TEXT.home, path: ROUTES.home.path, caption: TEXT.homeCaption },
    { label: TEXT.rulePlanner, path: ROUTES.rulePlanner.path, caption: TEXT.plannerCaption },
  ];

  return (
    <div className="route-shortcuts" aria-label={TEXT.quickPageShortcuts}>
      {items.map((item) => (
        <button
          key={item.path}
          type="button"
          className={`route-shortcut ${pathname === item.path ? "is-active" : ""}`}
          onClick={() => onNavigate(item.path)}
        >
          <strong>{item.label}</strong>
          <span>{item.caption}</span>
        </button>
      ))}
    </div>
  );
}

function HomePage({ onNavigate }) {
  return (
    <section className="feature-shell">
      <div className="panel quick-access-panel">
        <div className="panel-heading">
          <div>
            <p className="panel-kicker">{TEXT.quickAccess}</p>
            <h2>{TEXT.quickAccess}</h2>
          </div>
        </div>

        <div className="home-button-row">
          <button className="route-button" type="button" onClick={() => onNavigate(ROUTES.rulePlanner.path)}>
            {TEXT.quickButtonPlanner}
          </button>
        </div>
      </div>

      <article className="panel panel-featured route-card">
        <p className="panel-kicker">{TEXT.freePlanner}</p>
        <h2>{TEXT.plannerCardTitle}</h2>
        <p className="route-description">{TEXT.plannerCardDescription}</p>
        <div className="pill-row">
          <span className="pill">/rule-planner</span>
          <span className="pill">{TEXT.ruleBasedTag}</span>
        </div>
        <button className="route-button" type="button" onClick={() => onNavigate(ROUTES.rulePlanner.path)}>
          {TEXT.openPlanner}
        </button>
      </article>
    </section>
  );
}

function App() {
  const [pathname, setPathname] = useState(getCurrentPath);

  useEffect(() => {
    const handlePopState = () => setPathname(getCurrentPath());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const currentRoute =
    Object.values(ROUTES).find((route) => route.path === pathname) ?? ROUTES.home;

  return (
    <div className="app-shell">
      <div className="app-backdrop" />
      <main className="app-layout">
        <header className="hero">
          <div>
            <p className="hero-kicker">{TEXT.appKicker}</p>
            <h1>{currentRoute.title}</h1>
            <p className="hero-description">{currentRoute.description}</p>
          </div>

          <nav className="screen-tabs" aria-label={TEXT.featureNavigation}>
            <button
              type="button"
              className={`screen-tab ${pathname === ROUTES.home.path ? "is-active" : ""}`}
              onClick={() => navigate(ROUTES.home.path, setPathname)}
            >
              {TEXT.home}
            </button>
            <button
              type="button"
              className={`screen-tab ${pathname === ROUTES.rulePlanner.path ? "is-active" : ""}`}
              onClick={() => navigate(ROUTES.rulePlanner.path, setPathname)}
            >
              {TEXT.rulePlanner}
            </button>
          </nav>
        </header>

        <RouteShortcutList pathname={pathname} onNavigate={(path) => navigate(path, setPathname)} />

        {pathname === ROUTES.rulePlanner.path ? <RulePlanner /> : null}
        {pathname !== ROUTES.rulePlanner.path ? (
          <HomePage onNavigate={(path) => navigate(path, setPathname)} />
        ) : null}
      </main>
    </div>
  );
}

export default App;
