import { FormEvent, type CSSProperties, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PublicLayout } from "../../app/layouts/public-layout";
import { Button } from "../../shared/components/ui/button";
import { EmptyState } from "../../shared/components/feedback/empty-state";
import { useCommunityJournalsQuery } from "../../features/community/hooks/use-community-journals-query";
import "./landing-page.css";

const CITY_OPTIONS = [
  { value: "seoul", label: "서울" },
  { value: "busan", label: "부산" },
  { value: "jeju", label: "제주" },
];

const DURATION_OPTIONS = ["1박 2일", "2박 3일", "3박 4일"];

const COMPANION_OPTIONS = [
  { value: "solo", label: "혼자" },
  { value: "couple", label: "커플" },
  { value: "friend", label: "친구" },
  { value: "family", label: "가족" },
];

// 실제 스크린샷을 찍을 수단이 없어서, 결과 화면(2단계)과 같은 시각 언어로
// "서울 2박 3일" 예시를 손으로 만든 정적 목업이다 - 실제 존재하는 서울
// 장소 3곳을 예시로만 쓴다(평점·방문자 수 같은 지어낸 통계는 넣지 않았다).
const HERO_TIMELINE = [
  { time: "오전", name: "광화문", note: "수문장 교대식부터 가볍게 시작해요.", day: 1 },
  { time: "오후", name: "경복궁", note: "한복을 입으면 입장료 없이 들어갈 수 있어요.", day: 1 },
  { time: "저녁", name: "북촌한옥마을", note: "골목 사이로 전통 가옥을 둘러봐요.", day: 1 },
];

function dayColorStyle(day: number): CSSProperties {
  return {
    "--day-color": `var(--day-${day})`,
    "--day-color-text": `var(--day-${day}-text)`,
  } as CSSProperties;
}

export function LandingPage() {
  const navigate = useNavigate();
  const [city, setCity] = useState(CITY_OPTIONS[0].value);
  const [duration, setDuration] = useState(DURATION_OPTIONS[1]);
  const [companion, setCompanion] = useState(COMPANION_OPTIONS[2].value);

  const { data: journalData, isLoading: journalsLoading } = useCommunityJournalsQuery({
    page: 1,
    pageSize: 3,
    sort: "recommendations",
    keyword: "",
  });
  const journals = journalData?.items ?? [];

  const handleQuickStart = (event: FormEvent) => {
    event.preventDefault();
    navigate("/planner", {
      state: {
        quickStart: { city, duration_label: duration, companion_type: companion },
      },
    });
  };

  return (
    <PublicLayout>
      <div className="lp-root">
        <section className="lp-hero grid-12">
          <div className="lp-hero-copy">
            <h1 className="lp-hero-title">
              도시와 날짜만 고르면
              <br />
              동선은 Gonny가 짜드려요.
            </h1>
            <p className="lp-hero-desc">
              장소 사이 이동 시간까지 계산한 하루 일정을, 입력 몇 번으로 받아볼 수 있어요.
            </p>

            <form className="lp-quickstart" onSubmit={handleQuickStart}>
              <label className="lp-quickstart-field">
                <span>도시</span>
                <select onChange={(event) => setCity(event.target.value)} value={city}>
                  {CITY_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="lp-quickstart-field">
                <span>기간</span>
                <select onChange={(event) => setDuration(event.target.value)} value={duration}>
                  {DURATION_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
              <label className="lp-quickstart-field">
                <span>동행</span>
                <select onChange={(event) => setCompanion(event.target.value)} value={companion}>
                  {COMPANION_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <Button type="submit">일정 만들기 시작</Button>
            </form>

            <Link className="lp-hero-secondary-link" to="/inspiration">
              여행 이야기 먼저 둘러보기
            </Link>
          </div>

          <div aria-hidden="true" className="lp-hero-mock">
            <div className="lp-mock-card">
              <p className="lp-mock-title">서울 2박 3일 · 1일차</p>
              <div className="lp-mock-timeline">
                {HERO_TIMELINE.map((stop) => (
                  <div className="lp-mock-stop" key={stop.name} style={dayColorStyle(stop.day)}>
                    <span className="lp-mock-time">{stop.time}</span>
                    <div>
                      <strong>{stop.name}</strong>
                      <p>{stop.note}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <span aria-hidden="true" className="route-line lp-divider" />

        <section className="lp-feature grid-12">
          <div className="lp-feature-copy">
            <h2>도시와 기간을 고르면 하루 동선이 나와요</h2>
            <p>
              오전·오후·저녁 흐름에 맞춰 장소를 배치하고, 장소 사이 이동 시간까지 함께 계산해서
              보여드려요.
            </p>
          </div>
          <div className="lp-feature-visual">
            <div className="lp-mini-day" style={dayColorStyle(1)}>
              <span className="lp-mini-day-label">1일차</span>
              <p>오전 남산타워 · 오후 명동 · 저녁 한강공원</p>
            </div>
            <div className="lp-mini-day" style={dayColorStyle(2)}>
              <span className="lp-mini-day-label">2일차</span>
              <p>오전 익선동 · 오후 성수동 · 저녁 홍대</p>
            </div>
          </div>
        </section>

        <span aria-hidden="true" className="route-line lp-divider" />

        <section className="lp-feature grid-12">
          <div className="lp-feature-copy">
            <h2>비 소식이 있으면 실내 일정으로 바꿔드려요</h2>
            <p>여행 날짜에 비 예보가 있으면 미리 알려드리고, 실내에서 즐길 수 있는 대안을 추천해요.</p>
          </div>
          <div className="lp-feature-visual">
            <div className="lp-weather-mock">
              <p className="lp-weather-mock-title">2일차 오후, 비 예보가 있어요</p>
              <p className="lp-weather-mock-desc">실내에서 즐길 수 있는 대안 코스를 준비했어요.</p>
              <div className="lp-weather-mock-chips">
                <span className="chip">국립중앙박물관</span>
                <span className="chip">전통찻집 투어</span>
              </div>
            </div>
          </div>
        </section>

        <span aria-hidden="true" className="route-line lp-divider" />

        <section className="lp-feature grid-12">
          <div className="lp-feature-copy">
            <h2>다녀온 뒤엔 나만의 기록을 남겨요</h2>
            <p>사진과 글로 여행을 기록하면, 다른 여행자의 다음 일정에 힌트가 돼요.</p>
          </div>
          <div className="lp-feature-visual">
            {journalsLoading ? (
              <div className="lp-journal-list">
                {Array.from({ length: 3 }).map((_, index) => (
                  <div className="lp-journal-card lp-journal-card-loading" key={`journal-loading-${index}`} />
                ))}
              </div>
            ) : journals.length ? (
              <div className="lp-journal-list">
                {journals.map((journal) => (
                  <Link className="lp-journal-card" key={journal.id} to="/community/journals">
                    <strong>{journal.title || journal.trip_title}</strong>
                    <p>
                      {journal.destination} · 추천 {journal.recommendation_count}
                    </p>
                  </Link>
                ))}
              </div>
            ) : (
              <EmptyState
                description="가장 먼저 다녀온 여행을 기록해 보세요."
                title="아직 공개된 여행기록이 없어요."
              />
            )}
          </div>
        </section>

        <span aria-hidden="true" className="route-line lp-divider" />

        <section className="lp-feature grid-12">
          <div className="lp-feature-copy">
            <h2>동행자 취향까지 한 번에 맞춰요</h2>
            <p>함께 가는 사람의 취향을 등록하면, 그 취향에 맞는 장소를 일정에 함께 담아드려요.</p>
          </div>
          <div className="lp-feature-visual">
            <div className="lp-companion-mock">
              <span className="chip">파트너 · 미식</span>
              <span className="chip">친구 · 액티비티</span>
            </div>
          </div>
        </section>

        <section className="lp-closing">
          <h2>다른 여행자의 이야기도 둘러보세요</h2>
          <p>실제로 다녀온 사람들이 남긴 장소 기록이 다음 여행의 힌트가 될 수 있어요.</p>
          <Link to="/community">
            <Button variant="secondary">커뮤니티 둘러보기</Button>
          </Link>
        </section>
      </div>
    </PublicLayout>
  );
}
