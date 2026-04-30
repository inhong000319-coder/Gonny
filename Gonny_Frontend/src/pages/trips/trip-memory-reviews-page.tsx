import { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { useCreatePlaceReviewMutation } from "../../features/community/hooks/use-create-place-review-mutation";
import { useTripCommunityQuery } from "../../features/community/hooks/use-trip-community-query";
import {
  CreatePlaceReviewPayload,
  PlaceReview,
  PlaceSuggestion,
  TagSuggestion,
  UpdatePlaceReviewPayload,
} from "../../features/community/types/community";
import { useTripDetailQuery } from "../../features/trips/hooks/use-trip-detail-query";
import { apiClient } from "../../shared/api/client";
import { queryKeys } from "../../shared/api/query-keys";
import { Button } from "../../shared/components/ui/button";
import { ModalOverlay } from "../../shared/components/ui/modal-overlay";

const ratingOptions = [1, 2, 3, 4, 5];
const timeSlotOptions = ["이른 아침", "아침", "점심", "오후", "저녁", "밤"];
const companionOptions = [
  { value: "solo", label: "혼자" },
  { value: "friend", label: "친구" },
  { value: "couple", label: "커플" },
  { value: "family", label: "가족" },
];

type ReviewFormState = {
  city: string;
  place_name: string;
  rating: string;
  visit_time_slot: string;
  companion_type: string;
  recommended: boolean;
  would_revisit: boolean;
  tags: string;
  review_text: string;
};

function buildReviewForm(city: string): ReviewFormState {
  return {
    city,
    place_name: "",
    rating: "5",
    visit_time_slot: "저녁",
    companion_type: "friend",
    recommended: true,
    would_revisit: true,
    tags: "",
    review_text: "",
  };
}

function toCreatePayload(form: ReviewFormState, fallbackCity: string): CreatePlaceReviewPayload {
  return {
    city: form.city.trim() || fallbackCity,
    place_name: form.place_name.trim(),
    rating: Number(form.rating),
    visit_time_slot: form.visit_time_slot,
    companion_type: form.companion_type,
    recommended: form.recommended,
    would_revisit: form.would_revisit,
    tags: form.tags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean),
    review_text: form.review_text.trim(),
  };
}

function toUpdatePayload(form: ReviewFormState): UpdatePlaceReviewPayload {
  return {
    city: form.city.trim(),
    place_name: form.place_name.trim(),
    rating: Number(form.rating),
    visit_time_slot: form.visit_time_slot,
    companion_type: form.companion_type,
    recommended: form.recommended,
    would_revisit: form.would_revisit,
    tags: form.tags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean),
    review_text: form.review_text.trim(),
  };
}

function fromReview(review: PlaceReview): ReviewFormState {
  return {
    city: review.city,
    place_name: review.place_name,
    rating: String(review.rating),
    visit_time_slot: review.visit_time_slot ?? "저녁",
    companion_type: review.companion_type ?? "friend",
    recommended: review.recommended,
    would_revisit: review.would_revisit,
    tags: review.tags.join(", "),
    review_text: review.review_text,
  };
}

function formatDateTime(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function sortPlaceSuggestions(items: PlaceSuggestion[]) {
  return [...items].sort((left, right) => left.place_name.localeCompare(right.place_name, "ko-KR"));
}

function sortTagSuggestions(items: TagSuggestion[]) {
  return [...items].sort((left, right) => left.tag.localeCompare(right.tag, "ko-KR"));
}

function applyTagValue(previousValue: string, suggestion: string) {
  const parts = previousValue.split(",");
  parts[parts.length - 1] = ` ${suggestion}`;
  const nextValue = parts.join(",").replace(/^ /, "");
  return nextValue.endsWith(",") ? nextValue : `${nextValue}, `;
}

export function TripMemoryReviewsPage() {
  const { tripId = "" } = useParams();
  const queryClient = useQueryClient();
  const { data: tripDetail } = useTripDetailQuery(tripId);
  const { data, isLoading } = useTripCommunityQuery(tripId);
  const createReviewMutation = useCreatePlaceReviewMutation(tripId);

  const fallbackCity = tripDetail?.overview.destination ?? "";
  const reviews = data?.reviews ?? [];
  const placeStats = data?.place_stats ?? [];

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedReviewId, setSelectedReviewId] = useState<number | null>(null);
  const [isEditMode, setIsEditMode] = useState(false);
  const [reviewForm, setReviewForm] = useState<ReviewFormState>(buildReviewForm(fallbackCity));
  const [detailForm, setDetailForm] = useState<ReviewFormState>(buildReviewForm(fallbackCity));

  const [placeSuggestions, setPlaceSuggestions] = useState<PlaceSuggestion[]>([]);
  const [detailPlaceSuggestions, setDetailPlaceSuggestions] = useState<PlaceSuggestion[]>([]);
  const [tagSuggestions, setTagSuggestions] = useState<TagSuggestion[]>([]);
  const [detailTagSuggestions, setDetailTagSuggestions] = useState<TagSuggestion[]>([]);

  const [activePlaceSuggestionIndex, setActivePlaceSuggestionIndex] = useState(-1);
  const [activeDetailPlaceSuggestionIndex, setActiveDetailPlaceSuggestionIndex] = useState(-1);
  const [activeTagSuggestionIndex, setActiveTagSuggestionIndex] = useState(-1);
  const [activeDetailTagSuggestionIndex, setActiveDetailTagSuggestionIndex] = useState(-1);

  const selectedReview = useMemo(
    () => reviews.find((review) => review.id === selectedReviewId) ?? null,
    [reviews, selectedReviewId],
  );

  useEffect(() => {
    const keyword = reviewForm.place_name.trim();
    if (!keyword) {
      setPlaceSuggestions([]);
      setActivePlaceSuggestionIndex(-1);
      return;
    }

    const timer = window.setTimeout(async () => {
      try {
        const response = await apiClient.get<PlaceSuggestion[]>(`/trips/${tripId}/community/place-suggestions`, {
          params: { q: keyword },
        });
        const sorted = sortPlaceSuggestions(response.data);
        setPlaceSuggestions(sorted);
        setActivePlaceSuggestionIndex(sorted.length ? 0 : -1);
      } catch {
        setPlaceSuggestions([]);
        setActivePlaceSuggestionIndex(-1);
      }
    }, 180);

    return () => window.clearTimeout(timer);
  }, [reviewForm.place_name, tripId]);

  useEffect(() => {
    const keyword = detailForm.place_name.trim();
    if (!isEditMode || !keyword) {
      setDetailPlaceSuggestions([]);
      setActiveDetailPlaceSuggestionIndex(-1);
      return;
    }

    const timer = window.setTimeout(async () => {
      try {
        const response = await apiClient.get<PlaceSuggestion[]>(`/trips/${tripId}/community/place-suggestions`, {
          params: { q: keyword },
        });
        const sorted = sortPlaceSuggestions(response.data);
        setDetailPlaceSuggestions(sorted);
        setActiveDetailPlaceSuggestionIndex(sorted.length ? 0 : -1);
      } catch {
        setDetailPlaceSuggestions([]);
        setActiveDetailPlaceSuggestionIndex(-1);
      }
    }, 180);

    return () => window.clearTimeout(timer);
  }, [detailForm.place_name, isEditMode, tripId]);

  useEffect(() => {
    const reviewTagParts = reviewForm.tags.split(",");
    const token = reviewTagParts[reviewTagParts.length - 1]?.trim() ?? "";
    if (!token) {
      setTagSuggestions([]);
      setActiveTagSuggestionIndex(-1);
      return;
    }

    const timer = window.setTimeout(async () => {
      try {
        const response = await apiClient.get<TagSuggestion[]>(`/trips/${tripId}/community/tag-suggestions`, {
          params: { q: token },
        });
        const sorted = sortTagSuggestions(response.data);
        setTagSuggestions(sorted);
        setActiveTagSuggestionIndex(sorted.length ? 0 : -1);
      } catch {
        setTagSuggestions([]);
        setActiveTagSuggestionIndex(-1);
      }
    }, 180);

    return () => window.clearTimeout(timer);
  }, [reviewForm.tags, tripId]);

  useEffect(() => {
    const detailTagParts = detailForm.tags.split(",");
    const token = detailTagParts[detailTagParts.length - 1]?.trim() ?? "";
    if (!isEditMode || !token) {
      setDetailTagSuggestions([]);
      setActiveDetailTagSuggestionIndex(-1);
      return;
    }

    const timer = window.setTimeout(async () => {
      try {
        const response = await apiClient.get<TagSuggestion[]>(`/trips/${tripId}/community/tag-suggestions`, {
          params: { q: token },
        });
        const sorted = sortTagSuggestions(response.data);
        setDetailTagSuggestions(sorted);
        setActiveDetailTagSuggestionIndex(sorted.length ? 0 : -1);
      } catch {
        setDetailTagSuggestions([]);
        setActiveDetailTagSuggestionIndex(-1);
      }
    }, 180);

    return () => window.clearTimeout(timer);
  }, [detailForm.tags, isEditMode, tripId]);

  const invalidateCommunity = async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.tripCommunity(tripId) });
  };

  const updateReviewMutation = useMutation({
    mutationFn: async ({ reviewId, payload }: { reviewId: number; payload: UpdatePlaceReviewPayload }) => {
      const response = await apiClient.patch<PlaceReview>(`/trips/${tripId}/community/reviews/${reviewId}`, payload);
      return response.data;
    },
    onSuccess: async () => {
      setIsEditMode(false);
      await invalidateCommunity();
    },
  });

  const deleteReviewMutation = useMutation({
    mutationFn: async (reviewId: number) => {
      await apiClient.delete(`/trips/${tripId}/community/reviews/${reviewId}`);
    },
    onSuccess: async () => {
      setSelectedReviewId(null);
      setIsEditMode(false);
      await invalidateCommunity();
    },
  });

  const openCreateModal = () => {
    setReviewForm(buildReviewForm(fallbackCity));
    setPlaceSuggestions([]);
    setDetailPlaceSuggestions([]);
    setTagSuggestions([]);
    setDetailTagSuggestions([]);
    setActivePlaceSuggestionIndex(-1);
    setActiveDetailPlaceSuggestionIndex(-1);
    setActiveTagSuggestionIndex(-1);
    setActiveDetailTagSuggestionIndex(-1);
    setIsCreateModalOpen(true);
  };

  const openDetailModal = (review: PlaceReview) => {
    setSelectedReviewId(review.id);
    setDetailForm(fromReview(review));
    setDetailPlaceSuggestions([]);
    setDetailTagSuggestions([]);
    setActiveDetailPlaceSuggestionIndex(-1);
    setActiveDetailTagSuggestionIndex(-1);
    setIsEditMode(false);
  };

  const closeDetailModal = () => {
    setSelectedReviewId(null);
    setIsEditMode(false);
    setDetailPlaceSuggestions([]);
    setDetailTagSuggestions([]);
    setActiveDetailPlaceSuggestionIndex(-1);
    setActiveDetailTagSuggestionIndex(-1);
  };

  const applyPlaceSuggestion = (suggestion: PlaceSuggestion) => {
    setReviewForm((prev) => ({
      ...prev,
      city: suggestion.city ?? prev.city,
      place_name: suggestion.place_name,
    }));
    setPlaceSuggestions([]);
    setActivePlaceSuggestionIndex(-1);
  };

  const applyDetailPlaceSuggestion = (suggestion: PlaceSuggestion) => {
    setDetailForm((prev) => ({
      ...prev,
      city: suggestion.city ?? prev.city,
      place_name: suggestion.place_name,
    }));
    setDetailPlaceSuggestions([]);
    setActiveDetailPlaceSuggestionIndex(-1);
  };

  const applyTagSuggestion = (suggestion: TagSuggestion) => {
    setReviewForm((prev) => ({ ...prev, tags: applyTagValue(prev.tags, suggestion.tag) }));
    setTagSuggestions([]);
    setActiveTagSuggestionIndex(-1);
  };

  const applyDetailTagSuggestion = (suggestion: TagSuggestion) => {
    setDetailForm((prev) => ({ ...prev, tags: applyTagValue(prev.tags, suggestion.tag) }));
    setDetailTagSuggestions([]);
    setActiveDetailTagSuggestionIndex(-1);
  };

  const handleCreatePlaceKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (!placeSuggestions.length) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActivePlaceSuggestionIndex((prev) => (prev + 1) % placeSuggestions.length);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActivePlaceSuggestionIndex((prev) => (prev <= 0 ? placeSuggestions.length - 1 : prev - 1));
      return;
    }

    if (event.key === "Enter" && activePlaceSuggestionIndex >= 0) {
      event.preventDefault();
      applyPlaceSuggestion(placeSuggestions[activePlaceSuggestionIndex]);
    }
  };

  const handleDetailPlaceKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (!detailPlaceSuggestions.length) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveDetailPlaceSuggestionIndex((prev) => (prev + 1) % detailPlaceSuggestions.length);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveDetailPlaceSuggestionIndex((prev) =>
        prev <= 0 ? detailPlaceSuggestions.length - 1 : prev - 1,
      );
      return;
    }

    if (event.key === "Enter" && activeDetailPlaceSuggestionIndex >= 0) {
      event.preventDefault();
      applyDetailPlaceSuggestion(detailPlaceSuggestions[activeDetailPlaceSuggestionIndex]);
    }
  };

  const handleCreateTagKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (!tagSuggestions.length) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveTagSuggestionIndex((prev) => (prev + 1) % tagSuggestions.length);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveTagSuggestionIndex((prev) => (prev <= 0 ? tagSuggestions.length - 1 : prev - 1));
      return;
    }

    if (event.key === "Enter" && activeTagSuggestionIndex >= 0) {
      event.preventDefault();
      applyTagSuggestion(tagSuggestions[activeTagSuggestionIndex]);
    }
  };

  const handleDetailTagKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (!detailTagSuggestions.length) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveDetailTagSuggestionIndex((prev) => (prev + 1) % detailTagSuggestions.length);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveDetailTagSuggestionIndex((prev) =>
        prev <= 0 ? detailTagSuggestions.length - 1 : prev - 1,
      );
      return;
    }

    if (event.key === "Enter" && activeDetailTagSuggestionIndex >= 0) {
      event.preventDefault();
      applyDetailTagSuggestion(detailTagSuggestions[activeDetailTagSuggestionIndex]);
    }
  };

  const handleCreateSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await createReviewMutation.mutateAsync(toCreatePayload(reviewForm, fallbackCity));
    setIsCreateModalOpen(false);
    setReviewForm(buildReviewForm(fallbackCity));
    setPlaceSuggestions([]);
    setTagSuggestions([]);
  };

  const handleUpdateSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedReview) {
      return;
    }

    await updateReviewMutation.mutateAsync({
      reviewId: selectedReview.id,
      payload: toUpdatePayload(detailForm),
    });
  };

  if (!tripDetail) {
    return (
      <AppShell>
        <div className="card">
          <h2 className="section-title">장소 평가 화면을 준비하고 있어요.</h2>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <section className="page-hero panel panel-gradient">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <span className="section-kicker">PLACE REVIEWS</span>
            <h1 className="section-title" style={{ fontSize: "2.1rem", margin: "8px 0" }}>
              장소 평가
            </h1>
            <p className="section-subtitle" style={{ marginBottom: 0 }}>
              커뮤니티에 쌓인 장소 기록을 바탕으로 자동완성 추천을 받고, 내 평가를 남길 수 있어요.
            </p>
          </div>
          <div className="row">
            <Button onClick={openCreateModal}>평가 추가하기</Button>
            <Link to={`/trips/${tripId}/memory`}>
              <Button variant="secondary">기록 관리로 돌아가기</Button>
            </Link>
          </div>
        </div>
      </section>

      <section className="card stack">
        <div className="section-header">
          <div>
            <h2 className="section-title">기록된 장소 평가</h2>
            <p className="section-subtitle">상세보기에서 수정과 삭제까지 바로 이어집니다.</p>
          </div>
          <div className="chip-list">
            <span className="chip">전체 {reviews.length}개</span>
            <span className="chip">추천 {reviews.filter((review) => review.recommended).length}개</span>
          </div>
        </div>

        {isLoading ? <p className="section-subtitle">장소 평가를 불러오고 있어요.</p> : null}

        <div className="memory-scroll-list">
          {reviews.map((review) => (
            <article key={review.id} className="timeline-item community-entry-card memory-list-card">
              <div className="memory-list-head">
                <div>
                  <strong>{review.place_name}</strong>
                  <p className="community-meta-line">
                    {formatDateTime(review.created_at)} · {review.city} · {review.rating}점 ·{" "}
                    {review.recommended ? "추천해요" : "추천은 보류해요"}
                  </p>
                </div>
                <button className="button secondary" onClick={() => openDetailModal(review)} type="button">
                  상세보기
                </button>
              </div>
              <p className="community-entry-copy">{review.review_text}</p>
              <div className="chip-list">
                {review.tags.map((tag) => (
                  <span key={`${review.id}-${tag}`} className="chip">
                    {tag}
                  </span>
                ))}
              </div>
            </article>
          ))}

          {!isLoading && !reviews.length ? (
            <div className="admin-empty-card">
              <strong>아직 남겨진 장소 평가가 없어요.</strong>
              <p>평가 추가하기 버튼으로 첫 장소 평가를 남겨보세요.</p>
            </div>
          ) : null}
        </div>
      </section>

      <section className="card stack">
        <div>
          <h2 className="section-title">장소별 반응 요약</h2>
          <p className="section-subtitle">평균 평점과 추천 비율이 높은 장소를 한눈에 볼 수 있어요.</p>
        </div>
        <div className="memory-stats-grid">
          {placeStats.map((stat) => (
            <article key={stat.id} className="metric community-stat-card">
              <strong>{stat.place_name}</strong>
              <p className="community-meta-line">
                리뷰 {stat.review_count}개 · 평균 {stat.average_rating.toFixed(1)}점 · 추천 {formatPercent(stat.recommendation_rate)}
              </p>
              <div className="chip-list">
                {stat.top_tags.map((tag) => (
                  <span key={`${stat.id}-${tag}`} className="chip">
                    {tag}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>

      {isCreateModalOpen ? (
        <ModalOverlay className="memory-modal" onClose={() => setIsCreateModalOpen(false)}>
            <div className="section-header">
              <div>
                <h2 className="section-title">새 장소 평가 작성</h2>
                <p className="section-subtitle">
                  장소 이름과 태그를 입력하면 기존 커뮤니티 데이터 기준으로 자동완성 추천이 떠요.
                </p>
              </div>
              <button className="button ghost" onClick={() => setIsCreateModalOpen(false)} type="button">
                닫기
              </button>
            </div>

            <form className="stack" onSubmit={handleCreateSubmit}>
              <div className="community-inline-grid">
                <label className="field">
                  <span>자동 연결 지역</span>
                  <input readOnly value={reviewForm.city || fallbackCity} />
                </label>
                <label className="field field-suggestion">
                  <span>장소 이름</span>
                  <input
                    required
                    value={reviewForm.place_name}
                    onChange={(event) => {
                      setReviewForm((prev) => ({ ...prev, place_name: event.target.value }));
                      setActivePlaceSuggestionIndex(0);
                    }}
                    onKeyDown={handleCreatePlaceKeyDown}
                  />
                  {placeSuggestions.length ? (
                    <div className="suggestion-panel">
                      {placeSuggestions.map((suggestion, index) => (
                        <button
                          key={`${suggestion.city ?? "city"}-${suggestion.place_name}`}
                          className={`suggestion-item ${index === activePlaceSuggestionIndex ? "active" : ""}`}
                          onClick={() => applyPlaceSuggestion(suggestion)}
                          type="button"
                        >
                          <strong>{suggestion.place_name}</strong>
                          <span>
                            {suggestion.city ?? "도시 미기록"} · 리뷰 {suggestion.review_count}개
                          </span>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </label>
              </div>

              <div className="community-inline-grid">
                <label className="field">
                  <span>평점</span>
                  <select
                    value={reviewForm.rating}
                    onChange={(event) => setReviewForm((prev) => ({ ...prev, rating: event.target.value }))}
                  >
                    {ratingOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}점
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>방문 시간대</span>
                  <select
                    value={reviewForm.visit_time_slot}
                    onChange={(event) => setReviewForm((prev) => ({ ...prev, visit_time_slot: event.target.value }))}
                  >
                    {timeSlotOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="community-inline-grid">
                <label className="field">
                  <span>동행 유형</span>
                  <select
                    value={reviewForm.companion_type}
                    onChange={(event) => setReviewForm((prev) => ({ ...prev, companion_type: event.target.value }))}
                  >
                    {companionOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field field-suggestion">
                  <span>태그</span>
                  <input
                    value={reviewForm.tags}
                    onChange={(event) => {
                      setReviewForm((prev) => ({ ...prev, tags: event.target.value }));
                      setActiveTagSuggestionIndex(0);
                    }}
                    onKeyDown={handleCreateTagKeyDown}
                    placeholder="예: 칵테일, 야경 좋음, 친구 여행"
                  />
                  {tagSuggestions.length ? (
                    <div className="suggestion-panel">
                      {tagSuggestions.map((suggestion, index) => (
                        <button
                          key={suggestion.tag}
                          className={`suggestion-item ${index === activeTagSuggestionIndex ? "active" : ""}`}
                          onClick={() => applyTagSuggestion(suggestion)}
                          type="button"
                        >
                          <strong>{suggestion.tag}</strong>
                          <span>+{suggestion.count}</span>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </label>
              </div>

              <label className="field">
                <span>후기</span>
                <textarea
                  required
                  rows={6}
                  value={reviewForm.review_text}
                  onChange={(event) => setReviewForm((prev) => ({ ...prev, review_text: event.target.value }))}
                />
              </label>

              <div className="community-check-grid">
                <label className="row">
                  <input
                    checked={reviewForm.recommended}
                    onChange={(event) => setReviewForm((prev) => ({ ...prev, recommended: event.target.checked }))}
                    type="checkbox"
                  />
                  <span>다른 사람에게 추천하고 싶어요</span>
                </label>
                <label className="row">
                  <input
                    checked={reviewForm.would_revisit}
                    onChange={(event) => setReviewForm((prev) => ({ ...prev, would_revisit: event.target.checked }))}
                    type="checkbox"
                  />
                  <span>다시 방문할 의사가 있어요</span>
                </label>
              </div>

              <Button disabled={createReviewMutation.isPending} type="submit">
                {createReviewMutation.isPending ? "저장 중..." : "장소 평가 저장"}
              </Button>
            </form>
        </ModalOverlay>
      ) : null}

      {selectedReview ? (
        <ModalOverlay className="memory-modal memory-modal-wide" onClose={closeDetailModal}>
            <div className="section-header">
              <div>
                <h2 className="section-title">{selectedReview.place_name}</h2>
                <p className="community-meta-line">
                  {formatDateTime(selectedReview.created_at)} · {selectedReview.city} · {selectedReview.rating}점
                </p>
              </div>
              <div className="row">
                <button
                  className="button secondary"
                  onClick={() => {
                    setDetailForm(fromReview(selectedReview));
                    setDetailPlaceSuggestions([]);
                    setDetailTagSuggestions([]);
                    setActiveDetailPlaceSuggestionIndex(-1);
                    setActiveDetailTagSuggestionIndex(-1);
                    setIsEditMode((prev) => !prev);
                  }}
                  type="button"
                >
                  {isEditMode ? "수정 취소" : "수정"}
                </button>
                <button className="button ghost" onClick={closeDetailModal} type="button">
                  닫기
                </button>
              </div>
            </div>

            {isEditMode ? (
              <form className="stack" onSubmit={handleUpdateSubmit}>
                <div className="community-inline-grid">
                  <label className="field">
                    <span>자동 연결 지역</span>
                    <input readOnly value={detailForm.city || fallbackCity} />
                  </label>
                  <label className="field field-suggestion">
                    <span>장소 이름</span>
                    <input
                      value={detailForm.place_name}
                      onChange={(event) => {
                        setDetailForm((prev) => ({ ...prev, place_name: event.target.value }));
                        setActiveDetailPlaceSuggestionIndex(0);
                      }}
                      onKeyDown={handleDetailPlaceKeyDown}
                    />
                    {detailPlaceSuggestions.length ? (
                      <div className="suggestion-panel">
                        {detailPlaceSuggestions.map((suggestion, index) => (
                          <button
                            key={`${suggestion.city ?? "city"}-${suggestion.place_name}`}
                            className={`suggestion-item ${index === activeDetailPlaceSuggestionIndex ? "active" : ""}`}
                            onClick={() => applyDetailPlaceSuggestion(suggestion)}
                            type="button"
                          >
                            <strong>{suggestion.place_name}</strong>
                            <span>
                              {suggestion.city ?? "도시 미기록"} · 리뷰 {suggestion.review_count}개
                            </span>
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </label>
                </div>

                <div className="community-inline-grid">
                  <label className="field">
                    <span>평점</span>
                    <select
                      value={detailForm.rating}
                      onChange={(event) => setDetailForm((prev) => ({ ...prev, rating: event.target.value }))}
                    >
                      {ratingOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}점
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>방문 시간대</span>
                    <select
                      value={detailForm.visit_time_slot}
                      onChange={(event) => setDetailForm((prev) => ({ ...prev, visit_time_slot: event.target.value }))}
                    >
                      {timeSlotOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="community-inline-grid">
                  <label className="field">
                    <span>동행 유형</span>
                    <select
                      value={detailForm.companion_type}
                      onChange={(event) => setDetailForm((prev) => ({ ...prev, companion_type: event.target.value }))}
                    >
                      {companionOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field field-suggestion">
                    <span>태그</span>
                    <input
                      value={detailForm.tags}
                      onChange={(event) => {
                        setDetailForm((prev) => ({ ...prev, tags: event.target.value }));
                        setActiveDetailTagSuggestionIndex(0);
                      }}
                      onKeyDown={handleDetailTagKeyDown}
                    />
                    {detailTagSuggestions.length ? (
                      <div className="suggestion-panel">
                        {detailTagSuggestions.map((suggestion, index) => (
                          <button
                            key={suggestion.tag}
                            className={`suggestion-item ${index === activeDetailTagSuggestionIndex ? "active" : ""}`}
                            onClick={() => applyDetailTagSuggestion(suggestion)}
                            type="button"
                          >
                            <strong>{suggestion.tag}</strong>
                            <span>+{suggestion.count}</span>
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </label>
                </div>

                <label className="field">
                  <span>후기</span>
                  <textarea
                    rows={6}
                    value={detailForm.review_text}
                    onChange={(event) => setDetailForm((prev) => ({ ...prev, review_text: event.target.value }))}
                  />
                </label>

                <div className="community-check-grid">
                  <label className="row">
                    <input
                      checked={detailForm.recommended}
                      onChange={(event) => setDetailForm((prev) => ({ ...prev, recommended: event.target.checked }))}
                      type="checkbox"
                    />
                    <span>다른 사람에게 추천하고 싶어요</span>
                  </label>
                  <label className="row">
                    <input
                      checked={detailForm.would_revisit}
                      onChange={(event) => setDetailForm((prev) => ({ ...prev, would_revisit: event.target.checked }))}
                      type="checkbox"
                    />
                    <span>다시 방문할 의사가 있어요</span>
                  </label>
                </div>

                <div className="memory-modal-actions">
                  <Button disabled={updateReviewMutation.isPending} type="submit">
                    {updateReviewMutation.isPending ? "저장 중..." : "수정 저장"}
                  </Button>
                  <Button
                    disabled={deleteReviewMutation.isPending}
                    onClick={() => deleteReviewMutation.mutate(selectedReview.id)}
                    type="button"
                    variant="secondary"
                  >
                    삭제
                  </Button>
                </div>
              </form>
            ) : (
              <div className="stack">
                <div className="memory-summary-strip">
                  <strong>{selectedReview.place_name}</strong>
                  <span>
                    {selectedReview.visit_time_slot ?? "시간대 미기록"} ·{" "}
                    {selectedReview.companion_type ?? "동행 정보 없음"}
                  </span>
                </div>
                <p className="community-entry-copy">{selectedReview.review_text}</p>
                <div className="chip-list">
                  {selectedReview.tags.map((tag) => (
                    <span key={`${selectedReview.id}-${tag}`} className="chip">
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="chip-list">
                  <span className="chip">{selectedReview.recommended ? "추천해요" : "추천은 보류해요"}</span>
                  <span className="chip">{selectedReview.would_revisit ? "재방문 의사 있어요" : "재방문 의사는 없어요"}</span>
                </div>
              </div>
            )}
        </ModalOverlay>
      ) : null}
    </AppShell>
  );
}
