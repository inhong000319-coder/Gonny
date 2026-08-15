import { Link } from "react-router-dom";
import { PublicLayout } from "../../app/layouts/public-layout";
import { useAuth } from "../../app/providers/auth-provider";
import { useCommunityJournalsQuery } from "../../features/community/hooks/use-community-journals-query";
import { useTripsQuery } from "../../features/trips/hooks/use-trips-query";
import { Button } from "../../shared/components/ui/button";

const tripTones = ["rose", "aqua", "sky"];
const momentTones = ["peach", "blue", "mint"];

export function LandingPage() {
  const { isAuthenticated } = useAuth();
  const { data: trips = [] } = useTripsQuery(isAuthenticated);
  const { data: journalData, isLoading: journalsLoading } = useCommunityJournalsQuery({ page: 1, pageSize: 3, sort: "recommendations", keyword: "" });
  const tripCards = trips.slice(0, 3);
  const topJournals = journalData?.items ?? [];

  return (
    <PublicLayout>
      <div className="home-dashboard">
        <main className="home-feed">
          <section className="home-welcome-card">
            <div className="home-welcome-copy"><span className="home-script">Good morning, traveler</span><h1>Every journey<br />connects us.</h1><p>여행 계획부터 사람들이 남긴 진짜 장소 기록까지, Gonny에서 한 번에 만나보세요.</p><div className="home-welcome-actions"><Link to="/planner"><Button>여행 계획 시작하기</Button></Link><Link className="home-text-action" to="/inspiration">여행 이야기 보기 <span>→</span></Link></div></div>
            <div className="home-coast-art" aria-hidden="true"><span className="home-sun" /><span className="home-cloud cloud-one" /><span className="home-cloud cloud-two" /><span className="home-island island-one" /><span className="home-island island-two" /><span className="home-water" /></div>
            <div className="home-companion-strip"><span className="avatar-pile"><i>A</i><i>M</i><i>J</i></span><span>친구들과 함께 다음 여행을 계획해 보세요</span></div>
          </section>

          <section className="home-section">
            <div className="home-section-head"><div><span className="home-section-kicker">MY TRIPS</span><h2>나의 여행</h2></div><Link to="/trips">전체 보기</Link></div>
            <div className="home-trip-grid">
              {tripCards.length ? tripCards.map((trip, index) => <article className={`home-trip-card ${tripTones[index]}`} key={trip.id}><span>{trip.destination}</span><h3>{trip.title}</h3><p>{trip.startDate} - {trip.endDate}</p><Link to={`/trips/${trip.id}`}>일정 보기 <b>→</b></Link></article>) : <Link className="home-map-card" to="/planner"><span>WHERE TO NEXT?</span><strong>새로운 여행을<br />지도 위에 올려보세요.</strong><i>＋</i></Link>}
              {Array.from({ length: 3 - tripCards.length - (tripCards.length ? 0 : 1) }).map((_, index) => <div className="home-trip-empty-card" key={`empty-trip-${index}`} aria-label="비어 있는 여행 카드" />)}
            </div>
          </section>

          <section className="home-section">
            <div className="home-section-head"><div><span className="home-section-kicker">POPULAR TRAVEL STORIES</span><h2>인기 여행기록</h2></div><Link to="/community/journals">더 보기</Link></div>
            <div className="home-moment-grid">
              {journalsLoading ? Array.from({ length: 3 }).map((_, index) => <div className="home-moment-loading" key={`journal-loading-${index}`} />) : topJournals.map((journal, index) => <Link className={`home-moment-card ${momentTones[index % momentTones.length]}`} key={journal.id} to="/community/journals"><span className="moment-shape" /><span className="home-rank-badge">#{index + 1}</span><div><h3>{journal.title || journal.trip_title}</h3><p>{journal.destination} · 좋아요 {journal.recommendation_count}</p></div></Link>)}
              {!journalsLoading && !topJournals.length ? <div className="home-community-empty">아직 공개된 여행기록이 없어요.</div> : null}
            </div>
          </section>

          <section className="home-friends-card"><div className="home-friends-avatars"><i>Y</i><i>N</i><i>H</i><i>S</i></div><div><span className="home-section-kicker">TRAVEL WITH FRIENDS</span><strong>여행 기록을 공유하면, 다음 여행의 힌트가 됩니다.</strong></div><Link to="/login">로그인하기 →</Link></section>
        </main>
        <aside className="home-sidebar">
          <section className="quick-plan-card"><div className="home-panel-head"><div><span className="home-section-kicker">QUICK PLAN</span><h2>빠른 여행 계획</h2></div><Link to="/planner">전체</Link></div><div className="quick-plan-options"><Link to="/planner"><span className="quick-plan-icon blue">✦</span><div><strong>일정 추천</strong><small>조건으로 맞춤 코스 만들기</small></div></Link><Link to="/planner"><span className="quick-plan-icon sky">＋</span><div><strong>새 여행</strong><small>직접 일정을 시작하기</small></div></Link><Link to="/inspiration"><span className="quick-plan-icon mint">⌁</span><div><strong>장소 탐색</strong><small>여행자 평점으로 찾기</small></div></Link><Link to="/login"><span className="quick-plan-icon gold">☼</span><div><strong>여행 기록</strong><small>나만의 순간 남기기</small></div></Link></div></section>
          <section className="upcoming-card"><div className="home-panel-head"><div><span className="home-section-kicker">UPCOMING JOURNEY</span><h2>다음 여행의 시작</h2></div><Link to="/planner">수정</Link></div><div className="upcoming-route"><span>APR</span><div><strong>취향을 고르면</strong><small>나에게 맞는 동선이 만들어져요</small></div><b>01</b></div><div className="upcoming-map"><i className="map-pin pin-one" /><i className="map-pin pin-two" /><i className="map-route" /></div><Link className="upcoming-link" to="/planner">여행 조건 입력하기 <span>→</span></Link></section>
          <section className="home-promo-card"><span>TRAVEL BETTER TOGETHER</span><h2>좋은 여행은<br />좋은 이야기에서 시작돼요.</h2><Link to="/inspiration"><Button>커뮤니티 둘러보기</Button></Link><div className="promo-people" aria-hidden="true"><i /><i /><i /></div></section>
        </aside>
      </div>
    </PublicLayout>
  );
}
