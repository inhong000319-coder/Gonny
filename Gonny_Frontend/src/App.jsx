import { useEffect, useState } from "react";

import { AiTripTester } from "./features/ai-trip-tester/AiTripTester";
import { RulePlanner } from "./features/rule-planner/RulePlanner";

const TEXT = {
  appKicker: "\u0047\u006f\u006e\u006e\u0079 \ud504\ub860\ud2b8 \uc6cc\ud06c\uc2a4\ud398\uc774\uc2a4",
  homeTitle: "\u0047\u006f\u006e\u006e\u0079 \ud504\ub860\ud2b8 \uc6cc\ud06c\uc2a4\ud398\uc774\uc2a4",
  homeDescription:
    "\uaddc\uce59\uae30\ubc18 \uc77c\uc815 \uc0dd\uc131\uae30\uc640 \uae30\uc874 \ubc31\uc5d4\ub4dc \ud14c\uc2a4\ud2b8 \ud654\uba74 \uc911 \uc6d0\ud558\ub294 \ud398\uc774\uc9c0\ub85c \uc774\ub3d9\ud558\uc138\uc694.",
  plannerTitle: "\uaddc\uce59\uae30\ubc18 \uc77c\uc815 \uc0dd\uc131\uae30",
  plannerDescription:
    "\ub3c4\uc2dc \ub370\uc774\ud130\uc640 \uaddc\uce59\ub9cc\uc73c\ub85c \ub2e8\uacc4\ubcc4 \uc5ec\ud589 \uc77c\uc815\uc744 \ub9cc\ub4dc\ub294 \ud654\uba74\uc785\ub2c8\ub2e4.",
  aiTesterTitle: "\uae30\uc874 \u0054\u0072\u0069\u0070 \u0041\u0050\u0049 \ud14c\uc2a4\ud2b8",
  aiTesterDescription:
    "\ud604\uc7ac \u0054\u0072\u0069\u0070 \uc0dd\uc131\uacfc \uc77c\uc815 \uc0dd\uc131 \u0041\u0050\u0049\ub97c \uadf8\ub300\ub85c \ud14c\uc2a4\ud2b8\ud558\ub294 \ud654\uba74\uc785\ub2c8\ub2e4.",
  home: "\ud648",
  rulePlanner: "\uaddc\uce59\uae30\ubc18 \uc77c\uc815\uc0dd\uc131",
  aiTester: "\u0041\u0049 \ud14c\uc2a4\ud2b8",
  quickAccess: "\ud398\uc774\uc9c0 \ubc14\ub85c\uac00\uae30",
  quickButtonPlanner: "\uaddc\uce59\uae30\ubc18 \uc77c\uc815\uc0dd\uc131\uae30\ub85c \uc774\ub3d9",
  quickButtonAi: "\u0041\u0049 \ud14c\uc2a4\ud2b8 \ud654\uba74\uc73c\ub85c \uc774\ub3d9",
  freePlanner: "\ubb34\ub8cc \uc77c\uc815 \uc0dd\uc131",
  plannerCardTitle: "\uaddc\uce59\uae30\ubc18 \uc77c\uc815\uc0dd\uc131\uae30",
  plannerCardDescription:
    "\ub300\ub959, \uad6d\uac00, \ub3c4\uc2dc, \uc608\uc0b0, \uc5ec\ud589 \ucee8\uc149, \uc5ec\ud589 \uc2a4\ud0c0\uc77c\uc744 \ub2e8\uacc4\ubcc4\ub85c \uc120\ud0dd\ud574 \uaddc\uce59\uae30\ubc18 \uc77c\uc815\uc744 \uc0dd\uc131\ud569\ub2c8\ub2e4.",
  openPlanner: "\uaddc\uce59\uae30\ubc18 \uc77c\uc815\uc0dd\uc131\uae30 \uc5f4\uae30",
  backendCheck: "\ubc31\uc5d4\ub4dc \ud655\uc778",
  aiCardTitle: "\u0041\u0049 \ud14c\uc2a4\ud2b8",
  aiCardDescription:
    "\uae30\uc874 \uc5ec\ud589 \uc0dd\uc131, \uc77c\uc815 \uc0dd\uc131, \uc800\uc7a5\ub41c \u0074\u0072\u0069\u0070 \uc870\ud68c \ud750\ub984\uc744 \uadf8\ub300\ub85c \ud14c\uc2a4\ud2b8\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
  openAiTester: "\u0041\u0049 \ud14c\uc2a4\ud2b8 \uc5f4\uae30",
  homeCaption: "\uc6cc\ud06c\uc2a4\ud398\uc774\uc2a4 \uc2dc\uc791",
  plannerCaption: "\ub2e8\uacc4\ud615 \uc5ec\ud589 \ud50c\ub798\ub108",
  aiCaption: "\uae30\uc874 \ubc31\uc5d4\ub4dc \ud14c\uc2a4\ud2b8",
  quickPageShortcuts: "\ud398\uc774\uc9c0 \ubc14\ub85c\uac00\uae30",
  featureNavigation: "\uae30\ub2a5 \uc774\ub3d9",
  ruleBasedTag: "\uaddc\uce59\uae30\ubc18",
  existingFlowTag: "\uae30\uc874 \ud750\ub984",
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
  aiTester: {
    path: "/ai-tester",
    title: TEXT.aiTesterTitle,
    description: TEXT.aiTesterDescription,
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
    { label: TEXT.aiTester, path: ROUTES.aiTester.path, caption: TEXT.aiCaption },
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
          <button className="route-button secondary" type="button" onClick={() => onNavigate(ROUTES.aiTester.path)}>
            {TEXT.quickButtonAi}
          </button>
        </div>
      </div>

      <div className="two-column-grid">
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

        <article className="panel route-card">
          <p className="panel-kicker">{TEXT.backendCheck}</p>
          <h2>{TEXT.aiCardTitle}</h2>
          <p className="route-description">{TEXT.aiCardDescription}</p>
          <div className="pill-row">
            <span className="pill">/ai-tester</span>
            <span className="pill">{TEXT.existingFlowTag}</span>
          </div>
          <button className="route-button" type="button" onClick={() => onNavigate(ROUTES.aiTester.path)}>
            {TEXT.openAiTester}
          </button>
        </article>
      </div>
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
            <button
              type="button"
              className={`screen-tab ${pathname === ROUTES.aiTester.path ? "is-active" : ""}`}
              onClick={() => navigate(ROUTES.aiTester.path, setPathname)}
            >
              {TEXT.aiTester}
            </button>
          </nav>
        </header>

        <RouteShortcutList pathname={pathname} onNavigate={(path) => navigate(path, setPathname)} />

        {pathname === ROUTES.rulePlanner.path ? <RulePlanner /> : null}
        {pathname === ROUTES.aiTester.path ? <AiTripTester /> : null}
        {pathname !== ROUTES.rulePlanner.path && pathname !== ROUTES.aiTester.path ? (
          <HomePage onNavigate={(path) => navigate(path, setPathname)} />
        ) : null}
      </main>
    </div>
  );
}

export default App;
