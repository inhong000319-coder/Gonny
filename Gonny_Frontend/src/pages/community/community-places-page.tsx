import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "../../app/layouts/app-shell";
import { createPlaceReviewReaction } from "../../features/community/api/create-place-review-reaction";
import { useCommunityPlaceCitiesQuery } from "../../features/community/hooks/use-community-place-cities-query";
import { useCommunityPlaceDetailQuery } from "../../features/community/hooks/use-community-place-detail-query";
import { useCommunityPlacesQuery } from "../../features/community/hooks/use-community-places-query";
import { formatRegionLabel } from "../../features/community/lib/region-label";
import { CommunityPlaceReviewItem } from "../../features/community/types/community";
import { Button } from "../../shared/components/ui/button";
import { ModalOverlay } from "../../shared/components/ui/modal-overlay";

const reactionOptions = [
  { value: "like", emoji: "👍" },
  { value: "sad", emoji: "😢" },
  { value: "angry", emoji: "😠" },
  { value: "cheer", emoji: "❤️" },
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

function buildPageNumbers(page: number, totalPages: number) {
  const start = Math.max(1, page - 2);
  const end = Math.min(totalPages, start + 4);
  const pages: number[] = [];
  for (let current = start; current <= end; current += 1) {
    pages.push(current);
  }
  return pages;
}

function readReactionState() {
  if (typeof window === "undefined") {
    return {} as Record<string, boolean>;
  }
  try {
    const raw = window.localStorage.getItem("gonny:community-place-reactions");
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

function writeReactionState(state: Record<string, boolean>) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem("gonny:community-place-reactions", JSON.stringify(state));
}

export function CommunityPlacesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [keyword, setKeyword] = useState("");
  const [selectedCity, setSelectedCity] = useState("");
  const [selectedPlaceId, setSelectedPlaceId] = useState<number | null>(null);
  const [selectedRating, setSelectedRating] = useState<number | "all">("all");
  const [reactionState, setReactionState] = useState<Record<string, boolean>>(readReactionState);

  const { data: cities } = useCommunityPlaceCitiesQuery();
  const { data, isLoading } = useCommunityPlacesQuery({
    page,
    pageSize: 10,
    keyword,
    city: selectedCity,
  });
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

  const totalPages = useMemo(() => {
    if (!data) {
      return 1;
    }
    return Math.max(1, Math.ceil(data.total / data.page_size));
  }, [data]);
  const pages = buildPageNumbers(page, totalPages);

  const filteredReviews = useMemo(() => {
    const reviews = placeDetail?.reviews ?? [];
    if (selectedRating === "all") {
      return reviews;
    }
    return reviews.filter((review) => review.rating === selectedRating);
  }, [placeDetail?.reviews, selectedRating]);

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPage(1);
    setKeyword(searchInput);
  };

  const toggleReaction = async (review: CommunityPlaceReviewItem, reactionType: string, reactionCount: number) => {
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

  return (
    <AppShell>
      <section className="page-hero panel panel-gradient">
        <div className="stack">
          <span className="section-kicker">COMMUNITY PLACES</span>
          <h1 className="section-title" style={{ fontSize: "2.1rem", margin: 0 }}>
            장소 평가 전체 보기
          </h1>
          <p className="section-subtitle" style={{ marginBottom: 0 }}>
            먼저 지역을 고르고, 그 안에서 인기 장소를 살펴볼 수 있어요.
          </p>
        </div>
      </section>

      <section className="card stack">
        <form className="row" onSubmit={handleSearchSubmit} style={{ alignItems: "end", gap: "12px", flexWrap: "wrap" }}>
          <label className="field" style={{ minWidth: "200px" }}>
            <span>지역</span>
            <select
              value={selectedCity}
              onChange={(event) => {
                setSelectedCity(event.target.value);
                setPage(1);
              }}
            >
              <option value="">전체 지역</option>
              {cities?.map((city) => (
                <option key={city.city} value={city.city}>
                  {formatRegionLabel(city.city)} ({city.review_count})
                </option>
              ))}
            </select>
          </label>
          <label className="field" style={{ flex: 1, minWidth: "220px" }}>
            <span>인기 장소 검색</span>
            <input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="예: 스위치, 도쿄타워" />
          </label>
          <Button type="submit">검색하기</Button>
        </form>
      </section>

      <section className="card stack">
        {isLoading ? <p className="section-subtitle">장소 목록을 불러오고 있어요.</p> : null}

        <div className="memory-stats-grid">
          {data?.items.map((place) => (
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

        <div className="row" style={{ justifyContent: "center", gap: "8px", flexWrap: "wrap" }}>
          <button className="button secondary" disabled={page <= 1} onClick={() => setPage((prev) => prev - 1)} type="button">
            {"<"}
          </button>
          {pages.map((pageNumber) => (
            <button
              key={pageNumber}
              className={pageNumber === page ? "button" : "button secondary"}
              onClick={() => setPage(pageNumber)}
              type="button"
            >
              {pageNumber}
            </button>
          ))}
          <button
            className="button secondary"
            disabled={page >= totalPages}
            onClick={() => setPage((prev) => prev + 1)}
            type="button"
          >
            {">"}
          </button>
        </div>
      </section>

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
