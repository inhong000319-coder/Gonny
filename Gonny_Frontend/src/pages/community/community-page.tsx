import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { useAuth } from "../../app/providers/auth-provider";
import { CommunityJournalModal } from "../../features/community/components/community-journal-modal";
import { createPlaceReviewReaction } from "../../features/community/api/create-place-review-reaction";
import { getTripCommunity } from "../../features/community/api/get-trip-community";
import { useCommunityFeedQuery } from "../../features/community/hooks/use-community-feed-query";
import { useCommunityJournalsQuery } from "../../features/community/hooks/use-community-journals-query";
import { useCommunityPlaceDetailQuery } from "../../features/community/hooks/use-community-place-detail-query";
import { useCommunityTopPlacesQuery } from "../../features/community/hooks/use-community-top-places-query";
import { formatRegionLabel } from "../../features/community/region-label";
import "../../features/community/styles/community.css";
import { CommunityPlaceReviewItem } from "../../features/community/types/community";
import { useTripsQuery } from "../../features/trips/hooks/use-trips-query";
import { Button } from "../../shared/components/ui/button";
import { ModalOverlay } from "../../shared/components/ui/modal-overlay";

const reactionOptions = [
  { value: "like", emoji: "👍" },
  { value: "sad", emoji: "🥲" },
  { value: "angry", emoji: "😮" },
  { value: "cheer", emoji: "🙌" },
];

function formatDate(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat("ko-KR", { month: "long", day: "numeric" }).format(parsed);
}

function readReactionState() {
  try {
    const raw = window.localStorage.getItem("gonny:community-place-reactions");
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

export function CommunityPage() {
  const { user, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [featuredIndex, setFeaturedIndex] = useState(0);
  const [selectedJournalId, setSelectedJournalId] = useState<number | null>(null);
  const [selectedPlaceId, setSelectedPlaceId] = useState<number | null>(null);
  const [selectedRating, setSelectedRating] = useState<number | "all">("all");
  const [reactionState, setReactionState] = useState<Record<string, boolean>>(readReactionState);
  const { data: featuredData, isLoading: featuredLoading } = useCommunityJournalsQuery({ page: 1, pageSize: 5, sort: "recommendations", keyword: "" });
  const { data: latestFeed, isLoading: latestLoading } = useCommunityFeedQuery();
  const { data: topPlaces, isLoading: placesLoading } = useCommunityTopPlacesQuery();
  const { data: trips = [], isLoading: tripsLoading } = useTripsQuery(isAuthenticated);
  const { data: placeDetail, isLoading: placeDetailLoading } = useCommunityPlaceDetailQuery(selectedPlaceId);

  const { data: myStats } = useQuery({
    queryKey: ["my-community-stats", trips.map((trip) => trip.id)],
    enabled: isAuthenticated && !tripsLoading,
    queryFn: async () => {
      const communities = await Promise.all(trips.map((trip) => getTripCommunity(String(trip.id))));
      return communities.reduce(
        (stats, community) => ({
          posts: stats.posts + community.journals.length,
          comments: stats.comments + community.journals.reduce((count, journal) => count + journal.comments.filter((comment) => comment.author_id === String(user?.id)).length, 0),
        }),
        { posts: 0, comments: 0 },
      );
    },
  });

  const placeReactionMutation = useMutation({
    mutationFn: ({ tripId, reviewId, reactionType, delta }: { tripId: number; reviewId: number; reactionType: string; delta: number }) => createPlaceReviewReaction(tripId, reviewId, { reaction_type: reactionType, delta }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["community-place-detail", selectedPlaceId] }),
  });

  const featuredPosts = featuredData?.items ?? [];
  const featuredPost = featuredPosts[featuredIndex] ?? featuredPosts[0];
  const latestPosts = latestFeed?.journals.slice(0, 5) ?? [];
  const places = (topPlaces ?? []).slice(0, 4);
  const filteredReviews = useMemo(() => {
    const reviews = placeDetail?.reviews ?? [];
    return selectedRating === "all" ? reviews : reviews.filter((review) => review.rating === selectedRating);
  }, [placeDetail?.reviews, selectedRating]);

  const moveFeatured = (direction: number) => {
    if (featuredPosts.length) setFeaturedIndex((current) => (current + direction + featuredPosts.length) % featuredPosts.length);
  };

  const toggleReaction = async (review: CommunityPlaceReviewItem, reactionType: string, reactionCount: number) => {
    const key = `place:${review.id}:${reactionType}`;
    const wasActive = Boolean(reactionState[key] && reactionCount > 0);
    const updated = { ...reactionState, [key]: !wasActive };
    setReactionState(updated);
    window.localStorage.setItem("gonny:community-place-reactions", JSON.stringify(updated));
    try {
      await placeReactionMutation.mutateAsync({ tripId: review.trip_id, reviewId: review.id, reactionType, delta: wasActive ? -1 : 1 });
    } catch {
      const rollback = { ...reactionState, [key]: wasActive };
      setReactionState(rollback);
      window.localStorage.setItem("gonny:community-place-reactions", JSON.stringify(rollback));
    }
  };

  return (
    <AppShell>
      <div className="cm-home">
        <main className="cm-home-main">
          <section>
            <div className="cm-section-head">
              <div>
                <h1>이번 주 인기 여행기록</h1>
                <p>여행자들이 가장 많이 공감한 이야기에서 다음 여정을 찾아보세요.</p>
              </div>
              <Link to="/community/journals">전체 인기글 보기</Link>
            </div>
            {featuredLoading ? <div className="cm-skeleton" /> : null}
            {featuredPost ? (
              <article className="cm-feature-card">
                <span className="cm-feature-rank">인기 {featuredIndex + 1}위</span>
                <p className="community-meta-line">
                  {formatRegionLabel(featuredPost.destination)} · {featuredPost.trip_title}
                </p>
                <h3>{featuredPost.title}</h3>
                <p className="cm-feature-copy">{featuredPost.diary_text}</p>
                <div className="cm-feature-meta">
                  <span>좋아요 {featuredPost.recommendation_count}</span>
                  <span>조회 {featuredPost.view_count}</span>
                  <Button onClick={() => setSelectedJournalId(featuredPost.id)} variant="secondary">
                    기록 읽기
                  </Button>
                </div>
                {featuredPosts.length > 1 ? (
                  <div className="cm-slider-controls">
                    <button type="button" onClick={() => moveFeatured(-1)} aria-label="이전 인기글">
                      ‹
                    </button>
                    <div className="cm-slider-dots">
                      {featuredPosts.map((post, index) => (
                        <button
                          className={index === featuredIndex ? "active" : ""}
                          key={post.id}
                          type="button"
                          onClick={() => setFeaturedIndex(index)}
                          aria-label={`${index + 1}번째 인기글`}
                        />
                      ))}
                    </div>
                    <button type="button" onClick={() => moveFeatured(1)} aria-label="다음 인기글">
                      ›
                    </button>
                  </div>
                ) : null}
              </article>
            ) : !featuredLoading ? (
              <div className="cm-empty">아직 공개된 여행기록이 없어요.</div>
            ) : null}
          </section>

          <section>
            <div className="cm-section-head">
              <h2>지금 핫한 장소들</h2>
              <Link to="/community/places">장소 랭킹 보기</Link>
            </div>
            <div className="cm-place-grid">
              {placesLoading
                ? Array.from({ length: 4 }).map((_, index) => <div className="cm-skeleton" key={index} />)
                : null}
              {places.map((place, index) => (
                <button
                  className={`cm-place-tile${index === 0 ? " cm-place-tile--lead" : ""}`}
                  key={place.id}
                  type="button"
                  onClick={() => setSelectedPlaceId(place.id)}
                >
                  <span>{formatRegionLabel(place.city)}</span>
                  <strong>{place.place_name}</strong>
                  <p>
                    평점 {place.average_rating.toFixed(1)} · 리뷰 {place.review_count}
                  </p>
                  <div className="chip-list">
                    {place.top_tags.map((tag) => (
                      <span className="chip" key={tag}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          </section>

          <section>
            <div className="cm-section-head">
              <h2>새로 올라온 여행기록</h2>
              <Link to="/community/journals">전체글 보기</Link>
            </div>
            <div className="cm-latest-list">
              {latestLoading ? <p>새 기록을 불러오는 중이에요.</p> : null}
              {latestPosts.map((journal) => (
                <button key={journal.id} type="button" onClick={() => setSelectedJournalId(journal.id)}>
                  <div>
                    <strong>{journal.title}</strong>
                    <small>
                      {formatRegionLabel(journal.destination)} · {formatDate(journal.created_at)}
                    </small>
                  </div>
                </button>
              ))}
              {!latestLoading && !latestPosts.length ? (
                <div className="cm-empty">첫 여행기록을 커뮤니티에 공유해 보세요.</div>
              ) : null}
            </div>
          </section>
        </main>

        <aside className="cm-side">
          <section className="cm-side-card">
            <div className="cm-profile-name">
              <span className="cm-profile-avatar">{user?.nickname.slice(0, 1) ?? "G"}</span>
              <div>
                <h2>{user?.nickname ?? "여행자"}님</h2>
                <p className="community-meta-line">여행 이야기를 남겨볼까요?</p>
              </div>
            </div>
            <div className="cm-profile-stats">
              <div>
                <strong>{myStats?.posts ?? 0}</strong>
                <span>게시글</span>
              </div>
              <div>
                <strong>{myStats?.comments ?? 0}</strong>
                <span>댓글</span>
              </div>
              <div>
                <strong>{trips.length}</strong>
                <span>여행</span>
              </div>
            </div>
            <Link to="/profile">내 프로필 보기</Link>
          </section>

          <section className="cm-side-card">
            <h2>무엇을 찾아볼까요?</h2>
            <div className="cm-explore-list">
              <Link to="/community/journals">
                <strong>여행기록 둘러보기</strong>
                <p>여행자들의 생생한 후기</p>
              </Link>
              <Link to="/community/places">
                <strong>평점 좋은 장소</strong>
                <p>리뷰로 검증한 플레이스</p>
              </Link>
              <Link to="/trips">
                <strong>내 여행 기록하기</strong>
                <p>새로운 여정을 시작해요</p>
              </Link>
            </div>
          </section>

          <section className="cm-side-card">
            <h2>오늘의 커뮤니티</h2>
            <div className="cm-pulse-figure">
              <strong>{featuredData?.total ?? 0}</strong>
              <span>개의 공개 여행기록</span>
            </div>
            <p className="community-meta-line">좋아하는 여행기록에 공감하고, 나만의 장소 후기도 남겨보세요.</p>
            <Link to="/trips/recommend">
              <Button>새 여행 만들기</Button>
            </Link>
          </section>
        </aside>
      </div>

      {selectedJournalId !== null ? <CommunityJournalModal journalId={selectedJournalId} onClose={() => setSelectedJournalId(null)} /> : null}
      {selectedPlaceId !== null ? <ModalOverlay className="memory-modal memory-modal-wide" onClose={() => setSelectedPlaceId(null)}><div className="section-header"><div><h2 className="section-title">{formatRegionLabel(placeDetail?.place.city ?? "")} · {placeDetail?.place.place_name ?? "장소 리뷰"}</h2><p className="community-meta-line">평점 {placeDetail?.place.average_rating.toFixed(1) ?? "-"} · 리뷰 {placeDetail?.place.review_count ?? 0}개</p></div><button className="button ghost" type="button" onClick={() => setSelectedPlaceId(null)}>닫기</button></div><div className="chip-list"><button className={selectedRating === "all" ? "chip active" : "chip"} type="button" onClick={() => setSelectedRating("all")}>전체</button>{[5, 4, 3, 2, 1].map((rating) => <button className={selectedRating === rating ? "chip active" : "chip"} key={rating} type="button" onClick={() => setSelectedRating(rating)}>{rating}점</button>)}</div>{placeDetailLoading ? <p className="section-subtitle">장소 리뷰를 불러오는 중이에요.</p> : null}<div className="memory-scroll-list">{filteredReviews.map((review) => <article className="timeline-item community-entry-card memory-list-card" key={review.id}><div className="memory-list-head"><div><strong>{review.trip_title}</strong><p className="community-meta-line">{formatDate(review.created_at)} · {review.rating}점 · {review.visit_time_slot ?? "시간대 미기록"}</p></div></div><p className="community-entry-copy">{review.review_text}</p><div className="chip-list">{review.tags.map((tag) => <span className="chip" key={tag}>{tag}</span>)}</div><div className="memory-reaction-row">{reactionOptions.map((reaction) => { const count = review.reactions.find((item) => item.reaction_type === reaction.value)?.count ?? 0; const active = Boolean(reactionState[`place:${review.id}:${reaction.value}`] && count > 0); return <button className={`emotion-button compact ${active ? "active" : ""}`} key={reaction.value} type="button" onClick={() => toggleReaction(review, reaction.value, count)}><span className="emotion-button-emoji">{reaction.emoji}</span><span className="emotion-button-count">{count}</span></button>; })}</div></article>)}</div></ModalOverlay> : null}
    </AppShell>
  );
}
