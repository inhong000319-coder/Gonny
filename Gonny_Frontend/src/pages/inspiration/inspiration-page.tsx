import { AppShell } from "../../app/layouts/app-shell";

function FlowerIcon() {
  return (
    <svg aria-hidden="true" className="landing-feature-icon" fill="none" viewBox="0 0 24 24">
      <path
        d="M12 7.5c.8-2 3-3 4.7-2 1.6 1 1.8 3.2.4 4.6-1.1 1.1-3 .9-5.1-.3Zm0 0c-.8-2-3-3-4.7-2-1.6 1-1.8 3.2-.4 4.6 1.1 1.1 3 .9 5.1-.3Zm0 0c2-.8 3-3 2-4.7-1-1.6-3.2-1.8-4.6-.4-1.1 1.1-.9 3 .3 5.1Zm0 0c2 .8 3 3 2 4.7-1 1.6-3.2 1.8-4.6.4-1.1-1.1-.9-3 .3-5.1ZM12 11.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
    </svg>
  );
}

function TicketIcon() {
  return (
    <svg aria-hidden="true" className="landing-feature-icon" fill="none" viewBox="0 0 24 24">
      <path
        d="M6 7h12a2 2 0 0 1 2 2v2a2 2 0 0 0-2 2 2 2 0 0 0 2 2v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4V9a2 2 0 0 1 2-2Z"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path d="M9 7v10" stroke="currentColor" strokeDasharray="2 2" strokeWidth="1.8" />
    </svg>
  );
}

function CurrencyIcon() {
  return (
    <svg aria-hidden="true" className="landing-feature-icon" fill="none" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.8" />
      <path d="M14.5 8.5h-4a2 2 0 0 0 0 4h3a2 2 0 1 1 0 4h-4M12 7v10" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

const cards = [
  {
    icon: <FlowerIcon />,
    title: "시즌 추천",
    copy: "봄꽃, 여름 바다, 가을 단풍처럼 시기에 맞는 여행지를 더 직관적으로 보여줍니다.",
    accent: "cyan",
  },
  {
    icon: <TicketIcon />,
    title: "축제 캘린더",
    copy: "지역 이벤트를 단순 정보가 아니라 바로 일정 생성으로 이어지는 진입점으로 활용합니다.",
    accent: "violet",
  },
  {
    icon: <CurrencyIcon />,
    title: "실시간 환율",
    copy: "해외 확장 시 유용하고, 탐색 화면에서도 신뢰감을 더해주는 정보 카드 역할을 합니다.",
    accent: "amber",
  },
];

export function InspirationPage() {
  return (
    <AppShell>
      <section className="page-hero panel panel-gradient">
        <span className="section-kicker">Discovery mode</span>
        <h1 className="section-title" style={{ fontSize: "2.3rem", margin: "6px 0 10px" }}>
          영감이 바로 여행 계획으로 이어지는 화면
        </h1>
        <p className="section-subtitle" style={{ marginBottom: 0, maxWidth: 760 }}>
          플래너 화면보다 조금 더 가볍고 에디토리얼한 느낌을 주되, 전체 제품 톤은 그대로 유지합니다.
        </p>
      </section>

      <div className="page-grid inspiration-grid">
        {cards.map((card) => (
          <article className={`feature-panel feature-panel-${card.accent}`} key={card.title}>
            <div className="landing-feature-icon-wrap">{card.icon}</div>
            <h2>{card.title}</h2>
            <p>{card.copy}</p>
          </article>
        ))}
      </div>
    </AppShell>
  );
}
