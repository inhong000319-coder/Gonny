import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { CommunityJournalModal } from "../../features/community/components/community-journal-modal";
import { createPlaceReviewReaction } from "../../features/community/api/create-place-review-reaction";
import { useCommunityJournalsQuery } from "../../features/community/hooks/use-community-journals-query";
import { useCommunityPlaceDetailQuery } from "../../features/community/hooks/use-community-place-detail-query";
import { useCommunityTopPlacesQuery } from "../../features/community/hooks/use-community-top-places-query";
import { formatRegionLabel } from "../../features/community/lib/region-label";
import { CommunityPlaceReviewItem } from "../../features/community/types/community";
import { Button } from "../../shared/components/ui/button";
import { ModalOverlay } from "../../shared/components/ui/modal-overlay";

const reactionOptions = [
  { value: "like", label: "좋아요", emoji: "👍" },
  { value: "sad", label: "슬퍼요", emoji: "😢" },
  { value: "angry", label: "화나요", emoji: "😠" },
  { value: "cheer", label: "응원해요", emoji: "❤️" },
];

function formatDateTime(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(parsed);
}

function getReactionStorageKey() {
  return "gonny:community-place-reactions";
}

function readReactionState() {
  if (typeof window === "undefined") {
    return {} as Record<string, boolean>;
  }

  try {
    const raw = window.localStorage.getItem(getReactionStorageKey());
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

function writeReactionState(state: Record<string, boolean>) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(getReactionStorageKey(), JSON.stringify(state));
}

export function CommunityPage() {
  const queryClient = useQueryClient();
  const { data: journalData, isLoading: journalsLoading } = useCommunityJournalsQuery({
    page: 1,
    pageSize: 3,
    sort: "views",
    keyword: "",
  });
  const { data: topPlaces, isLoading: placesLoading } = useCommunityTopPlacesQuery();

  const [selectedJournalId, setSelectedJournalId] = useState<number | null>(null);
  const [selectedPlaceId, setSelectedPlaceId] = useState<number | null>(null);
  const [selectedRating, setSelectedRating] = useState<number | "all">("all");
  const [reactionState, setReactionState] = useState<Record<string, boolean>>(readReactionState);
  const { data: placeDetail, isLoading: placeDetailLoading } = useCommunityPlaceDetailQuery(selectedPlaceId);

  const placeReactionMutation = useMutation({
    mutationFn: async ({
      tripId,
      reviewId,
      reactionType,
      delta,
    }: {
      tripId: number;
      reviewId: number;
      reactionType: string;
      delta: number;
    }) => createPlaceReviewReaction(tripId, reviewId, { reaction_type: reactionType, delta }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["community-place-detail", selectedPlaceId] });
    },
  });

  const filteredReviews = useMemo(() => {
    const reviews = placeDetail?.reviews ?? [];
    if (selectedRating === "all") {
      return reviews;
    }
    return reviews.filter((review) => review.rating === selectedRating);
  }, [placeDetail?.reviews, selectedRating]);

  const toggleReaction = async (
    review: CommunityPlaceReviewItem,
    reactionType: string,
    reactionCount: number,
  ) => {
    const reactionKey = `place:${review.id}:${reactionType}`;
    const isActive = Boolean(reactionState[reactionKey] && reactionCount > 0);
    const nextState = !isActive;
    setReactionState((prev) => {
      const updated = { ...prev, [reactionKey]: nextState };
      writeReactionState(updated);
      return updated;
    });
    try {
      await placeReactionMutation.mutateAsync({
        tripId: review.trip_id,
        reviewId: review.id,
        reactionType,
        delta: isActive ? -1 : 1,
      });
    } catch {
      setReactionState((prev) => {
        const rolledBack = { ...prev, [reactionKey]: isActive };
        writeReactionState(rolledBack);
        return rolledBack;
      });
    }
  };

  const journals = journalData?.items ?? [];
  const places = topPlaces ?? [];
  const topJournal = journals[0] ?? null;
  const topPlace = places[0] ?? null;

  return (
    <AppShell>
      <section className="page-hero panel panel-gradient">
        <div className="stack">
          <span className="section-kicker">COMMUNITY</span>
          <h1 className="section-title" style={{ fontSize: "2.2rem", margin: 0 }}>
            여행 커뮤니티
          </h1>
          <p className="section-subtitle" style={{ marginBottom: 0 }}>
            사람들이 남긴 여행 기록과 장소 평가를 보고, 다음 여행에 참고할 수 있는 공간이에요.
          </p>
        </div>
      </section>

      {topJournal || topPlace ? (
        <section className="card stack community-spotlight-banner">
          <div className="section-header">
            <div>
              <span className="section-kicker">HOT NOW</span>
              <h2 className="section-title">지금 가장 뜨거운 인기 기록</h2>
              <p className="section-subtitle">조회수와 리뷰 수가 가장 높은 기록을 먼저 보여드려요.</p>
            </div>
          </div>
          <div className="community-spotlight-grid">
            {topJournal ? (
              <button className="community-spotlight-card" onClick={() => setSelectedJournalId(topJournal.id)} type="button">
                <span className="community-spotlight-badge">인기 다이어리 1위</span>
                <strong>{topJournal.title}</strong>
                <p>{topJournal.diary_text}</p>
                <div className="chip-list">
                  <span className="chip">조회수 {topJournal.view_count}</span>
                  <span className="chip">추천 {topJournal.recommendation_count}</span>
                </div>
              </button>
            ) : null}
            {topPlace ? (
              <button className="community-spotlight-card" onClick={() => setSelectedPlaceId(topPlace.id)} type="button">
                <span className="community-spotlight-badge">인기 장소 1위</span>
                <strong>
                  {formatRegionLabel(topPlace.city)} - {topPlace.place_name}
                </strong>
                <p>평점 {topPlace.average_rating.toFixed(1)}점 · 리뷰 {topPlace.review_count}개</p>
                <div className="chip-list">
                  {topPlace.top_tags.map((tag) => (
                    <span key={`${topPlace.id}-${tag}`} className="chip">
                      {tag}
                    </span>
                  ))}
                </div>
              </button>
            ) : null}
          </div>
        </section>
      ) : null}

      <section className="card stack">
        <div className="section-header">
          <div>
            <h2 className="section-title">공유된 여행 다이어리 TOP 3</h2>
            <p className="section-subtitle">조회수와 공감 수가 높은 다이어리부터 먼저 보여드려요.</p>
          </div>
          <Link to="/community/journals">
            <Button variant="secondary">전체 다이어리 보기</Button>
          </Link>
        </div>

        {journalsLoading ? <p className="section-subtitle">다이어리를 불러오고 있어요.</p> : null}

        <div className="stack">
          {journals.map((journal, index) => (
            <article key={journal.id} className="timeline-item community-entry-card">
              <div className="memory-list-head">
                <div>
                  <strong>
                    TOP {index + 1}. {journal.title}
                  </strong>
              <p className="community-meta-line">
                {journal.trip_title} · {formatRegionLabel(journal.destination)} · {formatDateTime(journal.created_at)}
              </p>
                </div>
                <button className="button secondary" onClick={() => setSelectedJournalId(journal.id)} type="button">
                  글 보기
                </button>
              </div>
              <p className="community-entry-copy">{journal.diary_text}</p>
              <div className="chip-list">
                <span className="chip">조회수 {journal.view_count}</span>
                <span className="chip">추천 {journal.recommendation_count}</span>
                {journal.overall_rating ? <span className="chip">만족도 {journal.overall_rating}점</span> : null}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="card stack">
        <div className="section-header">
          <div>
            <h2 className="section-title">사람들이 많이 남긴 장소 TOP 5</h2>
            <p className="section-subtitle">지역과 장소를 함께 보고, 클릭해서 그 장소 평가를 바로 확인해보세요.</p>
          </div>
          <Link to="/community/places">
            <Button variant="secondary">전체 장소 보기</Button>
          </Link>
        </div>

        {placesLoading ? <p className="section-subtitle">장소 데이터를 불러오고 있어요.</p> : null}

        <div className="memory-stats-grid">
          {places.map((place) => (
            <button
              key={place.id}
              className="metric community-stat-card"
              onClick={() => setSelectedPlaceId(place.id)}
              style={{ textAlign: "left", cursor: "pointer" }}
              type="button"
            >
              <strong>
                {formatRegionLabel(place.city)} - {place.place_name}
              </strong>
              <p className="community-meta-line">
                평점 {place.average_rating.toFixed(1)}점 · 리뷰 {place.review_count}개
              </p>
              <div className="chip-list">
                {place.top_tags.map((tag) => (
                  <span key={`${place.id}-${tag}`} className="chip">
                    {tag}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
      </section>

      {selectedJournalId !== null ? <CommunityJournalModal journalId={selectedJournalId} onClose={() => setSelectedJournalId(null)} /> : null}

      {selectedPlaceId !== null ? (
        <ModalOverlay className="memory-modal memory-modal-wide" onClose={() => setSelectedPlaceId(null)}>
            <div className="section-header">
              <div>
                <h2 className="section-title">
                  {formatRegionLabel(placeDetail?.place.city)} - {placeDetail?.place.place_name ?? "장소 평가"}
                </h2>
                <p className="community-meta-line">
                  평점 {placeDetail?.place.average_rating.toFixed(1) ?? "-"}점 · 리뷰 {placeDetail?.place.review_count ?? 0}개
                </p>
              </div>
              <button className="button ghost" onClick={() => setSelectedPlaceId(null)} type="button">
                닫기
              </button>
            </div>

            <div className="chip-list">
              <button className={selectedRating === "all" ? "chip active" : "chip"} onClick={() => setSelectedRating("all")} type="button">
                전체
              </button>
              {[5, 4, 3, 2, 1].map((rating) => (
                <button
                  key={rating}
                  className={selectedRating === rating ? "chip active" : "chip"}
                  onClick={() => setSelectedRating(rating)}
                  type="button"
                >
                  {rating}점
                </button>
              ))}
            </div>

            {placeDetailLoading ? <p className="section-subtitle">이 장소의 평가를 불러오고 있어요.</p> : null}

            <div className="memory-scroll-list">
              {filteredReviews.map((review) => (
                <article key={review.id} className="timeline-item community-entry-card memory-list-card">
                  <div className="memory-list-head">
                    <div>
                      <strong>{review.trip_title}</strong>
                      <p className="community-meta-line">
                        {formatDateTime(review.created_at)} · {review.rating}점 · {review.visit_time_slot ?? "시간대 미기록"}
                      </p>
                    </div>
                  </div>
                  <p className="community-entry-copy">{review.review_text}</p>
                  <div className="chip-list">
                    {review.tags.map((tag) => (
                      <span key={`${review.id}-${tag}`} className="chip">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="memory-reaction-row">
                    {reactionOptions.map((reaction) => {
                      const reactionCount =
                        review.reactions.find((item) => item.reaction_type === reaction.value)?.count ?? 0;
                      const reactionKey = `place:${review.id}:${reaction.value}`;
                      const isActive = Boolean(reactionState[reactionKey] && reactionCount > 0);
                      return (
                        <button
                          key={reaction.value}
                          className={`emotion-button compact ${isActive ? "active" : ""}`}
                          onClick={() => toggleReaction(review, reaction.value, reactionCount)}
                          type="button"
                        >
                          <span className="emotion-button-emoji">{reaction.emoji}</span>
                          <span className="emotion-button-count">{reactionCount}</span>
                        </button>
                      );
                    })}
                  </div>
                </article>
              ))}
            </div>
        </ModalOverlay>
      ) : null}
    </AppShell>
  );
}
