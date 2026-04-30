import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useCommunityJournalDetailQuery } from "../hooks/use-community-journal-detail-query";
import { formatRegionLabel } from "../lib/region-label";
import {
  CreateTravelJournalCommentPayload,
  TravelJournalComment,
  TravelJournalCommentReaction,
  TravelJournalReaction,
} from "../types/community";
import { JournalContentRenderer } from "./journal-content-renderer";
import { apiClient } from "../../../shared/api/client";
import { Button } from "../../../shared/components/ui/button";
import { ModalOverlay } from "../../../shared/components/ui/modal-overlay";

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
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function getReactionStorageKey(scopeKey: string) {
  return `gonny:community-reactions:${scopeKey}`;
}

function readReactionState(scopeKey: string) {
  if (typeof window === "undefined") {
    return {} as Record<string, boolean>;
  }

  try {
    const raw = window.localStorage.getItem(getReactionStorageKey(scopeKey));
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

function writeReactionState(scopeKey: string, state: Record<string, boolean>) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(getReactionStorageKey(scopeKey), JSON.stringify(state));
}

type Props = {
  journalId: number;
  onClose: () => void;
};

export function CommunityJournalModal({ journalId, onClose }: Props) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useCommunityJournalDetailQuery(journalId);
  const [commentDraft, setCommentDraft] = useState("");
  const [editingCommentId, setEditingCommentId] = useState<number | null>(null);
  const [editingCommentText, setEditingCommentText] = useState("");
  const [reactionState, setReactionState] = useState<Record<string, boolean>>({});

  const journal = data?.journal;

  useEffect(() => {
    setReactionState(readReactionState(`journal-${journalId}`));
  }, [journalId]);

  const invalidateDetail = async () => {
    await queryClient.invalidateQueries({ queryKey: ["community-journal-detail", journalId] });
    await queryClient.invalidateQueries({ queryKey: ["community-journals"] });
  };

  const createCommentMutation = useMutation({
    mutationFn: async ({ tripId, payload }: { tripId: number; payload: CreateTravelJournalCommentPayload }) => {
      const response = await apiClient.post(`/trips/${tripId}/community/journals/${journalId}/comments`, payload);
      return response.data;
    },
    onSuccess: async () => {
      setCommentDraft("");
      await invalidateDetail();
    },
  });

  const updateCommentMutation = useMutation({
    mutationFn: async ({ tripId, commentId, content }: { tripId: number; commentId: number; content: string }) => {
      const response = await apiClient.patch(`/trips/${tripId}/community/journals/${journalId}/comments/${commentId}`, {
        content,
      });
      return response.data;
    },
    onSuccess: async () => {
      setEditingCommentId(null);
      setEditingCommentText("");
      await invalidateDetail();
    },
  });

  const deleteCommentMutation = useMutation({
    mutationFn: async ({ tripId, commentId }: { tripId: number; commentId: number }) => {
      await apiClient.delete(`/trips/${tripId}/community/journals/${journalId}/comments/${commentId}`);
    },
    onSuccess: invalidateDetail,
  });

  const journalReactionMutation = useMutation({
    mutationFn: async ({ tripId, reactionType, delta }: { tripId: number; reactionType: string; delta: number }) => {
      const response = await apiClient.post(`/trips/${tripId}/community/journals/${journalId}/reactions`, {
        reaction_type: reactionType,
        delta,
      });
      return response.data;
    },
    onSuccess: invalidateDetail,
  });

  const commentReactionMutation = useMutation({
    mutationFn: async ({
      tripId,
      commentId,
      reactionType,
      delta,
    }: {
      tripId: number;
      commentId: number;
      reactionType: string;
      delta: number;
    }) => {
      const response = await apiClient.post(
        `/trips/${tripId}/community/journals/${journalId}/comments/${commentId}/reactions`,
        {
          reaction_type: reactionType,
          delta,
        },
      );
      return response.data;
    },
    onSuccess: invalidateDetail,
  });

  const toggleReaction = async (targetKey: string, request: () => Promise<unknown>) => {
    const nextState = !reactionState[targetKey];
    setReactionState((prev) => {
      const updated = { ...prev, [targetKey]: nextState };
      writeReactionState(`journal-${journalId}`, updated);
      return updated;
    });
    try {
      await request();
    } catch {
      setReactionState((prev) => {
        const rolledBack = { ...prev, [targetKey]: !nextState };
        writeReactionState(`journal-${journalId}`, rolledBack);
        return rolledBack;
      });
    }
  };

  if (isLoading || !journal || !data) {
    return (
      <ModalOverlay className="memory-modal memory-modal-wide" onClose={onClose}>
          <p className="section-subtitle">여행 다이어리를 불러오고 있어요.</p>
      </ModalOverlay>
    );
  }

  const handleCommentSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!commentDraft.trim()) {
      return;
    }

    await createCommentMutation.mutateAsync({
      tripId: journal.trip_id,
      payload: { content: commentDraft.trim() },
    });
  };

  return (
    <ModalOverlay className="memory-modal memory-modal-wide" onClose={onClose}>
        <div className="section-header">
          <div>
            <h2 className="section-title">{journal.title}</h2>
            <p className="community-meta-line">
              {data.trip_title} · {formatRegionLabel(data.destination)} · {formatDateTime(journal.created_at)}
            </p>
          </div>
          <div className="row">
            <Link to={`/trips/${journal.trip_id}`}>
              <Button variant="secondary">여행 상세보기</Button>
            </Link>
            <button className="button ghost" onClick={onClose} type="button">
              닫기
            </button>
          </div>
        </div>

        <div className="stack">
          <JournalContentRenderer blocks={journal.content_blocks} fallbackText={journal.diary_text} />
          {journal && false ? (
            <div className="journal-image-grid">
              {journal?.image_urls?.map((imageUrl, index) => (
                <img
                  key={`${imageUrl}-${index}`}
                  alt={`다이어리 이미지 ${index + 1}`}
                  className="journal-image-thumb"
                  src={imageUrl.startsWith("http") ? imageUrl : `http://localhost:8000${imageUrl}`}
                />
              ))}
            </div>
          ) : null}
          {journal.reflection_text ? (
            <div className="memory-summary-strip">
              <strong>다음 여행 메모</strong>
              <span>{journal.reflection_text}</span>
            </div>
          ) : null}
          <div className="chip-list">
            <span className="chip">조회수 {journal.view_count}</span>
            {journal.overall_rating ? <span className="chip">만족도 {journal.overall_rating}점</span> : null}
          </div>
          <div className="memory-reaction-row">
            {reactionOptions.map((reaction) => {
              const reactionCount =
                journal.reactions.find((item: TravelJournalReaction) => item.reaction_type === reaction.value)?.count ?? 0;
              const reactionKey = `journal:${journal.id}:${reaction.value}`;
              const isActive = Boolean(reactionState[reactionKey] && reactionCount > 0);
              return (
                <button
                  key={reaction.value}
                  className={`emotion-button ${isActive ? "active" : ""}`}
                  onClick={() =>
                    toggleReaction(reactionKey, () =>
                      journalReactionMutation.mutateAsync({
                        tripId: journal.trip_id,
                        reactionType: reaction.value,
                        delta: isActive ? -1 : 1,
                      }),
                    )
                  }
                  type="button"
                >
                  <span className="emotion-button-emoji">{reaction.emoji}</span>
                  <span className="emotion-button-label">{reaction.label}</span>
                  <span className="emotion-button-count">{reactionCount}</span>
                </button>
              );
            })}
          </div>
        </div>

        <section className="stack">
          <div className="section-header">
            <div>
              <h3 className="section-title">댓글</h3>
              <p className="section-subtitle">댓글에도 감정 공감을 남길 수 있어요.</p>
            </div>
          </div>

          <form className="stack" onSubmit={handleCommentSubmit}>
            <label className="field">
              <span>댓글 작성</span>
              <textarea rows={3} value={commentDraft} onChange={(event) => setCommentDraft(event.target.value)} />
            </label>
            <Button disabled={createCommentMutation.isPending} type="submit">
              {createCommentMutation.isPending ? "등록 중..." : "댓글 등록"}
            </Button>
          </form>

          <div className="memory-scroll-list memory-comment-list">
            {journal.comments.map((comment: TravelJournalComment) => (
              <article key={comment.id} className="timeline-item community-entry-card stack">
                <p className="community-meta-line">{formatDateTime(comment.created_at)}</p>
                {editingCommentId === comment.id ? (
                  <>
                    <textarea rows={3} value={editingCommentText} onChange={(event) => setEditingCommentText(event.target.value)} />
                    <div className="row">
                      <Button
                        onClick={() =>
                          updateCommentMutation.mutate({
                            tripId: journal.trip_id,
                            commentId: comment.id,
                            content: editingCommentText.trim(),
                          })
                        }
                        type="button"
                      >
                        댓글 저장
                      </Button>
                      <Button
                        onClick={() => {
                          setEditingCommentId(null);
                          setEditingCommentText("");
                        }}
                        type="button"
                        variant="ghost"
                      >
                        취소
                      </Button>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="community-entry-copy">{comment.content}</p>
                    <div className="memory-reaction-row">
                      {reactionOptions.map((reaction) => {
                        const reactionCount =
                          comment.reactions.find(
                            (item: TravelJournalCommentReaction) => item.reaction_type === reaction.value,
                          )?.count ?? 0;
                        const reactionKey = `comment:${comment.id}:${reaction.value}`;
                        const isActive = Boolean(reactionState[reactionKey] && reactionCount > 0);
                        return (
                          <button
                            key={reaction.value}
                            className={`emotion-button compact ${isActive ? "active" : ""}`}
                            onClick={() =>
                              toggleReaction(reactionKey, () =>
                                commentReactionMutation.mutateAsync({
                                  tripId: journal.trip_id,
                                  commentId: comment.id,
                                  reactionType: reaction.value,
                                  delta: isActive ? -1 : 1,
                                }),
                              )
                            }
                            type="button"
                          >
                            <span className="emotion-button-emoji">{reaction.emoji}</span>
                            <span className="emotion-button-count">{reactionCount}</span>
                          </button>
                        );
                      })}
                    </div>
                    <div className="row">
                      <Button
                        onClick={() => {
                          setEditingCommentId(comment.id);
                          setEditingCommentText(comment.content);
                        }}
                        type="button"
                        variant="secondary"
                      >
                        수정
                      </Button>
                      <Button
                        onClick={() =>
                          deleteCommentMutation.mutate({
                            tripId: journal.trip_id,
                            commentId: comment.id,
                          })
                        }
                        type="button"
                        variant="ghost"
                      >
                        삭제
                      </Button>
                    </div>
                  </>
                )}
              </article>
            ))}
          </div>
        </section>
    </ModalOverlay>
  );
}
