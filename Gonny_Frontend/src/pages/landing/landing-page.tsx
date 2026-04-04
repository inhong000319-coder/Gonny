import { Link } from "react-router-dom";
import { PublicLayout } from "../../app/layouts/public-layout";
import { Button } from "../../shared/components/ui/button";

function SparkIcon() {
  return (
    <svg aria-hidden="true" className="landing-mini-icon" viewBox="0 0 24 24">
      <path
        d="M12 2.5l1.95 5.55L19.5 10l-5.55 1.95L12 17.5l-1.95-5.55L4.5 10l5.55-1.95L12 2.5Zm6.25 12 1 2.75L22 18.25l-2.75 1-1 2.75-1-2.75-2.75-1 2.75-1 1-2.75Z"
        fill="currentColor"
      />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg aria-hidden="true" className="landing-feature-icon" fill="none" viewBox="0 0 24 24">
      <rect height="15" rx="4" stroke="currentColor" strokeWidth="1.8" width="16" x="4" y="6.5" />
      <path d="M8 3.5v5M16 3.5v5M4 10.5h16" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function PinIcon() {
  return (
    <svg aria-hidden="true" className="landing-feature-icon" fill="none" viewBox="0 0 24 24">
      <path
        d="M12 21s6-5.6 6-11a6 6 0 1 0-12 0c0 5.4 6 11 6 11Z"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <circle cx="12" cy="10" r="2.3" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function CompassIcon() {
  return (
    <svg aria-hidden="true" className="landing-feature-icon" fill="none" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.8" />
      <path d="M15.8 8.2 14 14l-5.8 1.8L10 10l5.8-1.8Z" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

const styleCards = [
  { emoji: "🏖", title: "휴양", copy: "바다와 여유 중심" },
  { emoji: "🗼", title: "관광", copy: "대표 스팟 위주" },
  { emoji: "⛰", title: "모험", copy: "액티브한 동선" },
  { emoji: "🍜", title: "미식", copy: "맛집과 카페 우선" },
];

const featureCards = [
  {
    icon: <SparkIcon />,
    title: "AI 맞춤 추천",
    copy: "취향, 예산, 여행 스타일을 조합해 일정 초안을 빠르게 생성합니다.",
  },
  {
    icon: <CalendarIcon />,
    title: "실시간 조율",
    copy: "날씨나 동행자 조건이 바뀌어도 장소 단위로 일정을 유연하게 수정할 수 있습니다.",
  },
  {
    icon: <PinIcon />,
    title: "완성형 플로우",
    copy: "숙소, 예산, 체크인, 공유, 회고까지 하나의 흐름 안에서 자연스럽게 이어집니다.",
  },
];

export function LandingPage() {
  return (
    <PublicLayout>
      <section className="landing-hero">
        <div className="landing-glow landing-glow-left" />
        <div className="landing-glow landing-glow-right" />

        <div className="landing-copy">
          <div className="landing-pill">
            <SparkIcon />
            <span>AI 기반 여행 플래너</span>
          </div>

          <h1 className="landing-title">첫 화면부터 취향이 느껴지는 여행 계획</h1>

          <p className="landing-description">
            카테고리 선택으로 빠르게 시작하고, 자연어로 더 섬세하게 다듬어보세요.
            색감 있고 정리된 흐름 안에서 AI가 여행 일정을 더 선명하게 잡아줍니다.
          </p>

          <div className="landing-actions">
            <Link to="/trips/new">
              <Button>여행 일정 만들기</Button>
            </Link>
            <Link to="/inspiration">
              <Button variant="secondary">영감 둘러보기</Button>
            </Link>
          </div>

          <div className="landing-style-grid">
            {styleCards.map((card) => (
              <div className="landing-style-card" key={card.title}>
                <span className="landing-style-emoji">{card.emoji}</span>
                <strong>{card.title}</strong>
                <span>{card.copy}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="landing-planner-card">
          <div className="landing-planner-top">
            <div>
              <span className="landing-card-eyebrow">Smart planner</span>
              <h2>밝고 직관적인 여행 준비</h2>
            </div>
            <div className="landing-badge">Beta</div>
          </div>

          <div className="landing-form-grid">
            <label className="landing-input-group">
              <span>출발일</span>
              <input defaultValue="2026-04-02" type="date" />
            </label>

            <label className="landing-input-group">
              <span>도착일</span>
              <input defaultValue="2026-04-08" type="date" />
            </label>
          </div>

          <label className="landing-input-group">
            <span>1인 기준 예산</span>
            <select defaultValue="budget-1">
              <option value="budget-1">50만원 이하</option>
              <option value="budget-2">50만원 ~ 100만원</option>
              <option value="budget-3">프리미엄</option>
            </select>
          </label>

          <div className="landing-style-picker">
            <div className="landing-picker-header">
              <CompassIcon />
              <span>여행 스타일</span>
            </div>

            <div className="landing-picker-grid">
              {styleCards.map((card) => (
                <button className="landing-picker-card" key={card.title} type="button">
                  <span className="landing-style-emoji">{card.emoji}</span>
                  <strong>{card.title}</strong>
                </button>
              ))}
            </div>
          </div>

          <div className="landing-people-row">
            <div className="landing-picker-header">
              <PinIcon />
              <span>여행 인원</span>
            </div>

            <div className="landing-stepper">
              <button type="button">-</button>
              <div>
                <strong>3</strong>
                <span>명</span>
              </div>
              <button type="button">+</button>
            </div>
          </div>

          <Link className="landing-cta-link" to="/trips/new">
            <Button className="landing-main-cta">AI 여행 일정 생성하기</Button>
          </Link>
        </div>
      </section>

      <section className="landing-feature-strip">
        {featureCards.map((card) => (
          <article className="landing-feature-card" key={card.title}>
            <div className="landing-feature-icon-wrap">{card.icon}</div>
            <h3>{card.title}</h3>
            <p>{card.copy}</p>
          </article>
        ))}
      </section>
    </PublicLayout>
  );
}
