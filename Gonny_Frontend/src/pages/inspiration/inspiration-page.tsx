import { AppShell } from "../../app/layouts/app-shell";
import { useSeasonalFeedQuery } from "../../features/inspiration/hooks/use-seasonal-feed-query";
import { Season } from "../../features/inspiration/api/get-seasonal-feed";
import "./inspiration-page.css";
import { useDocumentTitle } from "../../shared/hooks/use-document-title";

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
  useDocumentTitle("탐색");
  const seasonalFeedQuery = useSeasonalFeedQuery();
  const seasonalFeed = seasonalFeedQuery.data;

  return (
    <AppShell>
      <section className="ip-hero">
        <h1>지금 계절에 어울리는 여행지를 모아봤어요</h1>
        <p>서울·부산·제주의 인기 여행지와 이번 달 축제 정보를 한눈에 볼 수 있어요.</p>
      </section>

      <div className="ip-layout">
        <article className="ip-panel">
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

        <article className="ip-panel">
          <h2>축제 캘린더</h2>
          {seasonalFeedQuery.isLoading ? (
            <p>축제 정보를 불러오는 중이에요.</p>
          ) : seasonalFeedQuery.isError || !seasonalFeed ? (
            <p>지금은 축제 정보를 불러오지 못했어요.</p>
          ) : seasonalFeed.festivals.length > 0 ? (
            <div className="ip-festival-list">
              {seasonalFeed.festivals.slice(0, 5).map((festival, index) => (
                <div className="ip-festival-row" key={`${festival.city}-${festival.title}-${index}`}>
                  <strong>{festival.title}</strong>
                  <span>
                    {toCityLabel(festival.city)} · {festival.start_date} ~ {festival.end_date}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p>서울·부산·제주에 이번 달 등록된 축제 정보가 아직 없어요.</p>
          )}
        </article>
      </div>
    </AppShell>
  );
}
