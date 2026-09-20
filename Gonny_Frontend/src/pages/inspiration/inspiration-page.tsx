import { AppShell } from "../../app/layouts/app-shell";
import { useSeasonalFeedQuery } from "../../features/inspiration/hooks/use-seasonal-feed-query";
import { Season } from "../../features/inspiration/api/get-seasonal-feed";

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

const seasonLabelKo: Record<Season, string> = {
  spring: "봄",
  summer: "여름",
  autumn: "가을",
  winter: "겨울",
};

const cityLabelKo: Record<string, string> = {
  seoul: "서울",
  busan: "부산",
  jeju: "제주",
};

function toCityLabel(city: string) {
  return cityLabelKo[city] ?? city;
}

export function InspirationPage() {
  const seasonalFeedQuery = useSeasonalFeedQuery();
  const seasonalFeed = seasonalFeedQuery.data;

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
        <article className="feature-panel feature-panel-cyan">
          <div className="landing-feature-icon-wrap">
            <FlowerIcon />
          </div>
          <h2>시즌 추천</h2>
          {seasonalFeedQuery.isLoading ? (
            <p>시즌 정보를 불러오는 중이에요.</p>
          ) : seasonalFeedQuery.isError || !seasonalFeed ? (
            <p>지금은 시즌 추천 정보를 불러오지 못했어요.</p>
          ) : (
            <>
              <p>
                지금은 {seasonLabelKo[seasonalFeed.season]}이에요. 서울·부산·제주에서 지금 인기 있는 여행지를
                모아봤어요.
              </p>
              {seasonalFeed.popular_destinations.length > 0 ? (
                <div className="chip-list">
                  {seasonalFeed.popular_destinations.slice(0, 8).map((destination, index) => (
                    <span className="chip" key={`${destination.city}-${destination.title}-${index}`}>
                      {toCityLabel(destination.city)} · {destination.title}
                    </span>
                  ))}
                </div>
              ) : (
                <p>지금 보여드릴 인기 여행지가 아직 없어요.</p>
              )}
            </>
          )}
        </article>

        <article className="feature-panel feature-panel-violet">
          <div className="landing-feature-icon-wrap">
            <TicketIcon />
          </div>
          <h2>축제 캘린더</h2>
          {seasonalFeedQuery.isLoading ? (
            <p>축제 정보를 불러오는 중이에요.</p>
          ) : seasonalFeedQuery.isError || !seasonalFeed ? (
            <p>지금은 축제 정보를 불러오지 못했어요.</p>
          ) : seasonalFeed.festivals.length > 0 ? (
            <div className="stack" style={{ gap: 8 }}>
              {seasonalFeed.festivals.slice(0, 5).map((festival, index) => (
                <div key={`${festival.city}-${festival.title}-${index}`}>
                  <strong style={{ display: "block" }}>{festival.title}</strong>
                  <span style={{ color: "#61728d", fontSize: "0.85rem" }}>
                    {toCityLabel(festival.city)} · {festival.start_date} ~ {festival.end_date}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p>서울·부산·제주에 이번 달 등록된 축제 정보가 아직 없어요.</p>
          )}
        </article>

        <article className="feature-panel feature-panel-amber">
          <div className="landing-feature-icon-wrap">
            <CurrencyIcon />
          </div>
          <h2>실시간 환율</h2>
          <p>해외 확장 시 유용하고, 탐색 화면에서도 신뢰감을 더해주는 정보 카드 역할을 합니다.</p>
        </article>
      </div>
    </AppShell>
  );
}
