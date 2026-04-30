import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { AppShell } from "../../app/layouts/app-shell";
import { uploadJournalImage } from "../../features/community/api/upload-journal-image";
import { JournalContentEditor, JournalEditorBlock } from "../../features/community/components/journal-content-editor";
import { JournalContentRenderer } from "../../features/community/components/journal-content-renderer";
import { useTripCommunityQuery } from "../../features/community/hooks/use-trip-community-query";
import {
  CreateTravelJournalCommentPayload,
  CreateTravelJournalPayload,
  TravelJournal,
  TravelJournalComment,
  TravelJournalCommentReaction,
  TravelJournalContentBlock,
  TravelJournalReaction,
  UpdateTravelJournalPayload,
} from "../../features/community/types/community";
import { useTripDetailQuery } from "../../features/trips/hooks/use-trip-detail-query";
import { apiClient } from "../../shared/api/client";
import { queryKeys } from "../../shared/api/query-keys";
import { Button } from "../../shared/components/ui/button";
import { ModalOverlay } from "../../shared/components/ui/modal-overlay";

const ratingOptions = [1, 2, 3, 4, 5];
const reactionOptions = [
  { value: "like", label: "좋아요", emoji: "👍" },
  { value: "sad", label: "슬퍼요", emoji: "😢" },
  { value: "angry", label: "화나요", emoji: "😠" },
  { value: "cheer", label: "응원해요", emoji: "💖" },
];
const maxJournalImages = 20;

type JournalFormState = {
  title: string;
  reflection_text: string;
  overall_rating: number;
  share_with_community: boolean;
};

const emptyJournalForm: JournalFormState = {
  title: "",
  reflection_text: "",
  overall_rating: 5,
  share_with_community: true,
};

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

function formatDateLabel(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(parsed);
}

function getDateKey(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value.slice(0, 10);
  }

  const year = parsed.getFullYear();
  const month = `${parsed.getMonth() + 1}`.padStart(2, "0");
  const day = `${parsed.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function createTextEditorBlock(text = ""): JournalEditorBlock {
  return {
    id: `text-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    type: "text",
    text,
  };
}

function normalizeJournalBlocks(journal: TravelJournal | null): JournalEditorBlock[] {
  if (!journal) {
    return [createTextEditorBlock()];
  }

  const sourceBlocks = journal.content_blocks.length
    ? journal.content_blocks
    : [
        ...(journal.diary_text.trim()
          ? [
              {
                id: `fallback-text-${journal.id}`,
                type: "text" as const,
                text: journal.diary_text,
              },
            ]
          : []),
        ...journal.image_urls.map((url, index) => ({
          id: `fallback-image-${journal.id}-${index}`,
          type: "image" as const,
          url,
          caption: null,
          layout: "large" as const,
          aspect_ratio: "landscape" as const,
          overlay_text: null,
          emoji: null,
          crop_x: 50,
          crop_y: 50,
          crop_left: 0,
          crop_top: 0,
          crop_width: 100,
          crop_height: 100,
          width_percent: 100,
          zoom: 1,
          offset_x: 0,
          offset_y: 0,
          text_items: [],
          emoji_items: [],
          draw_items: [],
        })),
      ];

  const normalized = sourceBlocks.map<JournalEditorBlock>((block) => {
    if (block.type === "text") {
      return {
        id: block.id,
        type: "text",
        text: block.text ?? "",
        file: null,
        localPreviewUrl: null,
      };
    }

    return {
      id: block.id,
      type: "image",
      url: block.url ?? null,
      caption: block.caption ?? "",
      layout: block.layout ?? "large",
      aspect_ratio: block.aspect_ratio ?? "landscape",
      overlay_text: block.overlay_text ?? "",
      emoji: block.emoji ?? "",
      crop_x: block.crop_x ?? 50,
      crop_y: block.crop_y ?? 50,
      crop_left: block.crop_left ?? 0,
      crop_top: block.crop_top ?? 0,
      crop_width: block.crop_width ?? 100,
      crop_height: block.crop_height ?? 100,
      width_percent: block.width_percent ?? 100,
      zoom: block.zoom ?? 1,
      offset_x: block.offset_x ?? 0,
      offset_y: block.offset_y ?? 0,
      text_items: (block.text_items ?? []).map((item) => ({ ...item, rotation: item.rotation ?? 0, color: item.color ?? "#ffffff" })),
      emoji_items: (block.emoji_items ?? []).map((item) => ({ ...item, rotation: item.rotation ?? 0, color: item.color ?? "#ffffff" })),
      draw_items: block.draw_items ?? [],
      file: null,
      localPreviewUrl: null,
    };
  });

  return normalized.length ? normalized : [createTextEditorBlock()];
}

function countImageBlocks(blocks: JournalEditorBlock[]) {
  return blocks.filter((block) => block.type === "image").length;
}

function summarizeBlocks(blocks: JournalEditorBlock[]) {
  return blocks
    .filter((block) => block.type === "text")
    .map((block) => (block.text ?? "").trim())
    .filter(Boolean)
    .join("\n\n")
    .trim();
}

function hasRenderableBlocks(blocks: JournalEditorBlock[]) {
  return blocks.some((block) => {
    if (block.type === "text") {
      return Boolean(block.text?.trim());
    }
    return Boolean(block.url || block.localPreviewUrl || block.file);
  });
}

function buildJournalPreviewImage(journal: TravelJournal) {
  const imageBlock = journal.content_blocks.find((block) => block.type === "image" && block.url);
  const imageUrl = imageBlock?.url || journal.image_urls[0];
  if (!imageUrl) {
    return null;
  }
  return imageUrl.startsWith("http") ? imageUrl : `http://localhost:8000${imageUrl}`;
}

function buildDetailForm(journal: TravelJournal): JournalFormState {
  return {
    title: journal.title,
    reflection_text: journal.reflection_text ?? "",
    overall_rating: journal.overall_rating ?? 5,
    share_with_community: journal.share_with_community,
  };
}

function getReactionStorageKey(tripId: string) {
  return `gonny:trip-memory-reactions:${tripId}`;
}

function readReactionState(tripId: string): Record<string, boolean> {
  if (typeof window === "undefined") {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(getReactionStorageKey(tripId));
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

function writeReactionState(tripId: string, state: Record<string, boolean>) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(getReactionStorageKey(tripId), JSON.stringify(state));
}

async function uploadBlocks(tripId: string, blocks: JournalEditorBlock[]): Promise<TravelJournalContentBlock[]> {
  const uploadedBlocks: TravelJournalContentBlock[] = [];

  for (const block of blocks) {
    if (block.type === "text") {
      const text = (block.text ?? "").trim();
      if (!text) {
        continue;
      }
      uploadedBlocks.push({
        id: block.id,
        type: "text",
        text,
      });
      continue;
    }

    let nextUrl = block.url ?? "";
    if (block.file) {
      const uploaded = await uploadJournalImage(tripId, block.file);
      nextUrl = uploaded.url;
    }

    if (!nextUrl) {
      continue;
    }

    uploadedBlocks.push({
      id: block.id,
      type: "image",
      url: nextUrl,
      caption: block.caption?.trim() || null,
      layout: block.layout ?? "large",
      aspect_ratio: block.aspect_ratio ?? "landscape",
      overlay_text: block.overlay_text?.trim() || null,
      emoji: block.emoji?.trim() || null,
      crop_x: block.crop_x ?? 50,
      crop_y: block.crop_y ?? 50,
      crop_left: block.crop_left ?? 0,
      crop_top: block.crop_top ?? 0,
      crop_width: block.crop_width ?? 100,
      crop_height: block.crop_height ?? 100,
      width_percent: block.width_percent ?? 100,
      zoom: block.zoom ?? 1,
      offset_x: block.offset_x ?? 0,
      offset_y: block.offset_y ?? 0,
      text_items: (block.text_items ?? []).map((item) => ({
        id: item.id,
        text: item.text,
        x: item.x,
        y: item.y,
        size: item.size ?? 18,
        rotation: item.rotation ?? 0,
        color: item.color ?? "#ffffff",
      })),
      emoji_items: (block.emoji_items ?? []).map((item) => ({
        id: item.id,
        emoji: item.emoji,
        x: item.x,
        y: item.y,
        size: item.size ?? 34,
        rotation: item.rotation ?? 0,
        color: item.color ?? "#ffffff",
      })),
      draw_items: (block.draw_items ?? []).map((item) => ({
        id: item.id,
        color: item.color,
        size: item.size,
        points: item.points.map((point) => ({ x: point.x, y: point.y })),
      })),
    });
  }

  return uploadedBlocks;
}

function buildJournalPayload(form: JournalFormState, contentBlocks: TravelJournalContentBlock[]): CreateTravelJournalPayload {
  const diaryText = contentBlocks
    .filter((block) => block.type === "text")
    .map((block) => block.text?.trim() ?? "")
    .filter(Boolean)
    .join("\n\n")
    .trim();

  const imageUrls = contentBlocks
    .filter((block) => block.type === "image" && block.url)
    .map((block) => block.url as string);

  return {
    title: form.title.trim(),
    diary_text: diaryText,
    reflection_text: form.reflection_text.trim() || null,
    content_blocks: contentBlocks,
    image_urls: imageUrls,
    overall_rating: form.overall_rating,
    share_with_community: form.share_with_community,
  };
}

export function TripMemoryDiaryPage() {
  const { tripId = "101" } = useParams();
  const queryClient = useQueryClient();
  const { data: tripDetail } = useTripDetailQuery(tripId);
  const { data, isLoading } = useTripCommunityQuery(tripId);

  const [reactionState, setReactionState] = useState<Record<string, boolean>>({});
  const [selectedDateKey, setSelectedDateKey] = useState("all");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedJournalId, setSelectedJournalId] = useState<number | null>(null);
  const [isEditMode, setIsEditMode] = useState(false);
  const [journalForm, setJournalForm] = useState<JournalFormState>(emptyJournalForm);
  const [detailForm, setDetailForm] = useState<JournalFormState>(emptyJournalForm);
  const [createBlocks, setCreateBlocks] = useState<JournalEditorBlock[]>([createTextEditorBlock()]);
  const [detailBlocks, setDetailBlocks] = useState<JournalEditorBlock[]>([createTextEditorBlock()]);
  const [commentDraft, setCommentDraft] = useState("");
  const [editingCommentId, setEditingCommentId] = useState<number | null>(null);
  const [editingCommentText, setEditingCommentText] = useState("");

  useEffect(() => {
    setReactionState(readReactionState(tripId));
  }, [tripId]);

  const journals = useMemo(() => data?.journals ?? [], [data]);
  const availableDates = useMemo(() => {
    const keys = Array.from(new Set(journals.map((journal) => getDateKey(journal.created_at))));
    return keys.sort((left, right) => (left < right ? 1 : -1));
  }, [journals]);

  useEffect(() => {
    if (selectedDateKey !== "all" && !availableDates.includes(selectedDateKey)) {
      setSelectedDateKey("all");
    }
  }, [availableDates, selectedDateKey]);

  const filteredJournals = useMemo(() => {
    if (selectedDateKey === "all") {
      return journals;
    }
    return journals.filter((journal) => getDateKey(journal.created_at) === selectedDateKey);
  }, [journals, selectedDateKey]);

  const groupedJournals = useMemo(() => {
    return filteredJournals.reduce<Array<{ dateKey: string; label: string; items: TravelJournal[] }>>((acc, journal) => {
      const dateKey = getDateKey(journal.created_at);
      const lastGroup = acc[acc.length - 1];

      if (!lastGroup || lastGroup.dateKey !== dateKey) {
        acc.push({
          dateKey,
          label: formatDateLabel(journal.created_at),
          items: [journal],
        });
        return acc;
      }

      lastGroup.items.push(journal);
      return acc;
    }, []);
  }, [filteredJournals]);

  const selectedJournal = useMemo(
    () => journals.find((journal) => journal.id === selectedJournalId) ?? null,
    [journals, selectedJournalId],
  );

  useEffect(() => {
    if (!selectedJournal || isEditMode) {
      return;
    }
    setDetailForm(buildDetailForm(selectedJournal));
    setDetailBlocks(normalizeJournalBlocks(selectedJournal));
  }, [selectedJournal, isEditMode]);

  const invalidateCommunity = async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.tripCommunity(tripId) });
    await queryClient.invalidateQueries({ queryKey: ["community-journals"] });
    await queryClient.invalidateQueries({ queryKey: ["community-journal-detail", selectedJournalId] });
  };

  const createJournalMutation = useMutation({
    mutationFn: async (payload: CreateTravelJournalPayload) => {
      const response = await apiClient.post<TravelJournal>(`/trips/${tripId}/community/journals`, payload);
      return response.data;
    },
    onSuccess: async (journal) => {
      setIsCreateModalOpen(false);
      setJournalForm(emptyJournalForm);
      setCreateBlocks([createTextEditorBlock()]);
      setSelectedJournalId(journal.id);
      await invalidateCommunity();
    },
  });

  const updateJournalMutation = useMutation({
    mutationFn: async ({ journalId, payload }: { journalId: number; payload: UpdateTravelJournalPayload }) => {
      const response = await apiClient.patch<TravelJournal>(`/trips/${tripId}/community/journals/${journalId}`, payload);
      return response.data;
    },
    onSuccess: async () => {
      setIsEditMode(false);
      await invalidateCommunity();
    },
  });

  const deleteJournalMutation = useMutation({
    mutationFn: async (journalId: number) => {
      await apiClient.delete(`/trips/${tripId}/community/journals/${journalId}`);
    },
    onSuccess: async () => {
      setSelectedJournalId(null);
      setIsEditMode(false);
      await invalidateCommunity();
    },
  });

  const createCommentMutation = useMutation({
    mutationFn: async ({ journalId, payload }: { journalId: number; payload: CreateTravelJournalCommentPayload }) => {
      const response = await apiClient.post(`/trips/${tripId}/community/journals/${journalId}/comments`, payload);
      return response.data;
    },
    onSuccess: async () => {
      setCommentDraft("");
      await invalidateCommunity();
    },
  });

  const updateCommentMutation = useMutation({
    mutationFn: async ({
      journalId,
      commentId,
      content,
    }: {
      journalId: number;
      commentId: number;
      content: string;
    }) => {
      const response = await apiClient.patch(`/trips/${tripId}/community/journals/${journalId}/comments/${commentId}`, {
        content,
      });
      return response.data;
    },
    onSuccess: async () => {
      setEditingCommentId(null);
      setEditingCommentText("");
      await invalidateCommunity();
    },
  });

  const deleteCommentMutation = useMutation({
    mutationFn: async ({ journalId, commentId }: { journalId: number; commentId: number }) => {
      await apiClient.delete(`/trips/${tripId}/community/journals/${journalId}/comments/${commentId}`);
    },
    onSuccess: invalidateCommunity,
  });

  const reactionMutation = useMutation({
    mutationFn: async ({
      journalId,
      reactionType,
      delta,
    }: {
      journalId: number;
      reactionType: string;
      delta: number;
    }) => {
      const response = await apiClient.post(`/trips/${tripId}/community/journals/${journalId}/reactions`, {
        reaction_type: reactionType,
        delta,
      });
      return response.data;
    },
    onSuccess: invalidateCommunity,
  });

  const commentReactionMutation = useMutation({
    mutationFn: async ({
      journalId,
      commentId,
      reactionType,
      delta,
    }: {
      journalId: number;
      commentId: number;
      reactionType: string;
      delta: number;
    }) => {
      const response = await apiClient.post(`/trips/${tripId}/community/journals/${journalId}/comments/${commentId}/reactions`, {
        reaction_type: reactionType,
        delta,
      });
      return response.data;
    },
    onSuccess: invalidateCommunity,
  });

  const toggleReaction = async (targetKey: string, request: () => Promise<unknown>) => {
    const nextState = !reactionState[targetKey];
    setReactionState((prev) => {
      const updated = { ...prev, [targetKey]: nextState };
      writeReactionState(tripId, updated);
      return updated;
    });
    try {
      await request();
    } catch {
      setReactionState((prev) => {
        const rolledBack = { ...prev, [targetKey]: !nextState };
        writeReactionState(tripId, rolledBack);
        return rolledBack;
      });
    }
  };

  const openCreateModal = () => {
    setJournalForm(emptyJournalForm);
    setCreateBlocks([createTextEditorBlock()]);
    setIsCreateModalOpen(true);
  };

  const openJournalDetail = (journal: TravelJournal) => {
    setSelectedJournalId(journal.id);
    setIsEditMode(false);
    setDetailForm(buildDetailForm(journal));
    setDetailBlocks(normalizeJournalBlocks(journal));
  };

  const handleCreateJournal = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!journalForm.title.trim()) {
      return;
    }
    if (!hasRenderableBlocks(createBlocks)) {
      return;
    }

    const uploadedBlocks = await uploadBlocks(tripId, createBlocks);
    const payload = buildJournalPayload(journalForm, uploadedBlocks);
    await createJournalMutation.mutateAsync(payload);
  };

  const handleUpdateJournal = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedJournal || !detailForm.title.trim()) {
      return;
    }
    if (!hasRenderableBlocks(detailBlocks)) {
      return;
    }

    const uploadedBlocks = await uploadBlocks(tripId, detailBlocks);
    const payload = buildJournalPayload(detailForm, uploadedBlocks);
    await updateJournalMutation.mutateAsync({
      journalId: selectedJournal.id,
      payload,
    });
  };

  const handleCommentSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedJournal || !commentDraft.trim()) {
      return;
    }

    await createCommentMutation.mutateAsync({
      journalId: selectedJournal.id,
      payload: { content: commentDraft.trim() },
    });
  };

  if (isLoading) {
    return (
      <AppShell>
        <section className="panel">
          <p className="section-subtitle">여행 다이어리를 불러오는 중이에요.</p>
        </section>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <section className="panel stack">
        <div className="section-header">
          <div>
            <p className="section-kicker">TRAVEL DIARY</p>
            <h1 className="section-title">
              {tripDetail?.overview.title || `${tripDetail?.overview.destination || "여행"} 다이어리`}
            </h1>
            <p className="section-subtitle">
              사진, 문단, 메모를 함께 엮어서 여행을 오래 남길 수 있는 다이어리 페이지예요.
            </p>
          </div>
          <div className="row">
            <Link to={`/trips/${tripId}/memory`}>
              <Button variant="secondary">기록 관리 허브</Button>
            </Link>
            <Button onClick={openCreateModal}>글 작성</Button>
          </div>
        </div>

        <div className="chip-list">
          <button
            className={`chip ${selectedDateKey === "all" ? "active" : ""}`}
            onClick={() => setSelectedDateKey("all")}
            type="button"
          >
            전체 보기
          </button>
          {availableDates.map((dateKey) => (
            <button
              key={dateKey}
              className={`chip ${selectedDateKey === dateKey ? "active" : ""}`}
              onClick={() => setSelectedDateKey(dateKey)}
              type="button"
            >
              {formatDateLabel(dateKey)}
            </button>
          ))}
        </div>

        <div className="stack">
          {groupedJournals.length ? (
            groupedJournals.map((group) => (
              <section className="stack" key={group.dateKey}>
                <div className="section-header">
                  <div>
                    <h2 className="section-title">{group.label}</h2>
                    <p className="section-subtitle">{group.items.length}개의 기록이 남아 있어요.</p>
                  </div>
                </div>
                <div className="memory-list-scroll">
                  {group.items.map((journal) => {
                    const previewImageUrl = buildJournalPreviewImage(journal);
                    return (
                      <article className="timeline-item community-entry-card stack" key={journal.id}>
                        <div className="section-header">
                          <div>
                            <h3 className="section-title">{journal.title}</h3>
                            <p className="community-meta-line">{formatDateTime(journal.created_at)}</p>
                          </div>
                          <div className="chip-list">
                            {journal.share_with_community ? <span className="chip">공유 공개</span> : <span className="chip">나만 보기</span>}
                            {journal.overall_rating ? <span className="chip">만족도 {journal.overall_rating}점</span> : null}
                          </div>
                        </div>
                        {previewImageUrl ? (
                          <div className="journal-image-block layout-medium">
                            <div className="journal-image-frame aspect-landscape">
                              <img alt={journal.title} className="journal-image-thumb" src={previewImageUrl} />
                            </div>
                          </div>
                        ) : null}
                        <p className="community-entry-copy">{summarizeBlocks(normalizeJournalBlocks(journal)) || journal.diary_text}</p>
                        <div className="row">
                          <Button onClick={() => openJournalDetail(journal)} variant="secondary">
                            상세 보기
                          </Button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>
            ))
          ) : (
            <div className="empty-state">
              <h2>아직 이 날짜에 남긴 다이어리가 없어요.</h2>
              <p>여행에서 기억하고 싶은 순간을 사진과 함께 남겨보세요.</p>
            </div>
          )}
        </div>
      </section>

      {isCreateModalOpen ? (
        <ModalOverlay className="memory-modal memory-modal-wide" onClose={() => setIsCreateModalOpen(false)}>
            <form className="stack" onSubmit={handleCreateJournal}>
              <div className="section-header">
                <div>
                  <h2 className="section-title">새 다이어리 작성</h2>
                  <p className="section-subtitle">문단 사이사이에 사진을 넣고, 원하는 순서로 배치할 수 있어요.</p>
                </div>
                <button className="button ghost" onClick={() => setIsCreateModalOpen(false)} type="button">
                  닫기
                </button>
              </div>

              <div className="form-grid">
                <label className="field">
                  <span>제목</span>
                  <input
                    className="input"
                    placeholder="예: 첫날의 노을과 야시장"
                    value={journalForm.title}
                    onChange={(event) => setJournalForm((prev) => ({ ...prev, title: event.target.value }))}
                  />
                </label>
                <label className="field">
                  <span>다음 여행 메모</span>
                  <input
                    className="input"
                    placeholder="다음 여행에서 꼭 다시 해보고 싶은 것을 적어보세요."
                    value={journalForm.reflection_text}
                    onChange={(event) => setJournalForm((prev) => ({ ...prev, reflection_text: event.target.value }))}
                  />
                </label>
              </div>

              <div className="row">
                <span className="section-subtitle">이번 기록 만족도</span>
                <div className="chip-list">
                  {ratingOptions.map((rating) => (
                    <button
                      key={rating}
                      className={`chip ${journalForm.overall_rating === rating ? "active" : ""}`}
                      onClick={() => setJournalForm((prev) => ({ ...prev, overall_rating: rating }))}
                      type="button"
                    >
                      {rating}점
                    </button>
                  ))}
                </div>
              </div>

              <label className="memory-todo-check">
                <input
                  checked={journalForm.share_with_community}
                  type="checkbox"
                  onChange={(event) => setJournalForm((prev) => ({ ...prev, share_with_community: event.target.checked }))}
                />
                <span>커뮤니티에 이 다이어리를 공유할게요.</span>
              </label>

              <JournalContentEditor
                blocks={createBlocks}
                imageCount={countImageBlocks(createBlocks)}
                maxImages={maxJournalImages}
                onChange={setCreateBlocks}
              />

              <div className="row">
                <button className="button secondary" onClick={() => setIsCreateModalOpen(false)} type="button">
                  취소
                </button>
                <Button disabled={createJournalMutation.isPending} type="submit">
                  {createJournalMutation.isPending ? "저장 중..." : "다이어리 저장"}
                </Button>
              </div>
            </form>
        </ModalOverlay>
      ) : null}

      {selectedJournal ? (
        <ModalOverlay className="memory-modal memory-modal-wide" onClose={() => setSelectedJournalId(null)}>
            <div className="section-header">
              <div>
                <h2 className="section-title">{selectedJournal.title}</h2>
                <p className="community-meta-line">{formatDateTime(selectedJournal.created_at)}</p>
              </div>
              <div className="row">
                <Link to={`/trips/${tripId}`}>
                  <Button variant="secondary">여행 상세보기</Button>
                </Link>
                <button className="button ghost" onClick={() => setSelectedJournalId(null)} type="button">
                  닫기
                </button>
              </div>
            </div>

            {isEditMode ? (
              <form className="stack" onSubmit={handleUpdateJournal}>
                <div className="form-grid">
                  <label className="field">
                    <span>제목</span>
                    <input
                      className="input"
                      value={detailForm.title}
                      onChange={(event) => setDetailForm((prev) => ({ ...prev, title: event.target.value }))}
                    />
                  </label>
                  <label className="field">
                    <span>다음 여행 메모</span>
                    <input
                      className="input"
                      value={detailForm.reflection_text}
                      onChange={(event) => setDetailForm((prev) => ({ ...prev, reflection_text: event.target.value }))}
                    />
                  </label>
                </div>

                <div className="row">
                  <span className="section-subtitle">이번 기록 만족도</span>
                  <div className="chip-list">
                    {ratingOptions.map((rating) => (
                      <button
                        key={rating}
                        className={`chip ${detailForm.overall_rating === rating ? "active" : ""}`}
                        onClick={() => setDetailForm((prev) => ({ ...prev, overall_rating: rating }))}
                        type="button"
                      >
                        {rating}점
                      </button>
                    ))}
                  </div>
                </div>

                <label className="memory-todo-check">
                  <input
                    checked={detailForm.share_with_community}
                    type="checkbox"
                    onChange={(event) => setDetailForm((prev) => ({ ...prev, share_with_community: event.target.checked }))}
                  />
                  <span>커뮤니티에 이 다이어리를 공유할게요.</span>
                </label>

                <JournalContentEditor
                  blocks={detailBlocks}
                  imageCount={countImageBlocks(detailBlocks)}
                  maxImages={maxJournalImages}
                  onChange={setDetailBlocks}
                />

                <div className="row">
                  <button className="button secondary" onClick={() => setIsEditMode(false)} type="button">
                    편집 취소
                  </button>
                  <button
                    className="button secondary"
                    onClick={() => deleteJournalMutation.mutate(selectedJournal.id)}
                    type="button"
                  >
                    삭제
                  </button>
                  <Button disabled={updateJournalMutation.isPending} type="submit">
                    {updateJournalMutation.isPending ? "수정 중..." : "수정 저장"}
                  </Button>
                </div>
              </form>
            ) : (
              <div className="stack">
                <JournalContentRenderer blocks={selectedJournal.content_blocks} fallbackText={selectedJournal.diary_text} />
                {selectedJournal.reflection_text ? (
                  <div className="memory-summary-strip">
                    <strong>다음 여행 메모</strong>
                    <span>{selectedJournal.reflection_text}</span>
                  </div>
                ) : null}
                <div className="chip-list">
                  <span className="chip">조회수 {selectedJournal.view_count}</span>
                  {selectedJournal.overall_rating ? <span className="chip">만족도 {selectedJournal.overall_rating}점</span> : null}
                  {selectedJournal.share_with_community ? <span className="chip">공유 공개</span> : <span className="chip">나만 보기</span>}
                </div>
                <div className="memory-reaction-row">
                  {reactionOptions.map((reaction) => {
                    const reactionCount =
                      selectedJournal.reactions.find((item: TravelJournalReaction) => item.reaction_type === reaction.value)?.count ?? 0;
                    const reactionKey = `journal:${selectedJournal.id}:${reaction.value}`;
                    const isActive = Boolean(reactionState[reactionKey] && reactionCount > 0);
                    return (
                      <button
                        key={reaction.value}
                        className={`emotion-button ${isActive ? "active" : ""}`}
                        onClick={() =>
                          toggleReaction(reactionKey, () =>
                            reactionMutation.mutateAsync({
                              journalId: selectedJournal.id,
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
                <div className="row">
                  <Button onClick={() => setIsEditMode(true)} variant="secondary">
                    수정하기
                  </Button>
                  <button
                    className="button secondary"
                    onClick={() => deleteJournalMutation.mutate(selectedJournal.id)}
                    type="button"
                  >
                    삭제하기
                  </button>
                </div>

                <section className="stack">
                  <div className="section-header">
                    <div>
                      <h3 className="section-title">댓글</h3>
                      <p className="section-subtitle">함께 여행을 복기하고 공감도 남겨보세요.</p>
                    </div>
                  </div>

                  <form className="stack" onSubmit={handleCommentSubmit}>
                    <textarea
                      className="textarea"
                      placeholder="이 기록에 남기고 싶은 한마디를 적어보세요."
                      rows={3}
                      value={commentDraft}
                      onChange={(event) => setCommentDraft(event.target.value)}
                    />
                    <div className="row">
                      <Button disabled={createCommentMutation.isPending} type="submit">
                        댓글 남기기
                      </Button>
                    </div>
                  </form>

                  <div className="memory-list-scroll">
                    {selectedJournal.comments.map((comment: TravelJournalComment) => (
                      <article className="timeline-item community-entry-card stack" key={comment.id}>
                        <div className="section-header">
                          <div>
                            <strong>{comment.author_name || "여행 메모 손님"}</strong>
                            <p className="community-meta-line">{formatDateTime(comment.created_at)}</p>
                          </div>
                          <div className="row">
                            <button
                              className="button ghost"
                              onClick={() => {
                                setEditingCommentId(comment.id);
                                setEditingCommentText(comment.content);
                              }}
                              type="button"
                            >
                              수정
                            </button>
                            <button
                              className="button ghost"
                              onClick={() =>
                                deleteCommentMutation.mutate({
                                  journalId: selectedJournal.id,
                                  commentId: comment.id,
                                })
                              }
                              type="button"
                            >
                              삭제
                            </button>
                          </div>
                        </div>

                        {editingCommentId === comment.id ? (
                          <form
                            className="stack"
                            onSubmit={async (event) => {
                              event.preventDefault();
                              if (!editingCommentText.trim()) {
                                return;
                              }

                              await updateCommentMutation.mutateAsync({
                                journalId: selectedJournal.id,
                                commentId: comment.id,
                                content: editingCommentText.trim(),
                              });
                            }}
                          >
                            <textarea
                              className="textarea"
                              rows={3}
                              value={editingCommentText}
                              onChange={(event) => setEditingCommentText(event.target.value)}
                            />
                            <div className="row">
                              <button
                                className="button secondary"
                                onClick={() => {
                                  setEditingCommentId(null);
                                  setEditingCommentText("");
                                }}
                                type="button"
                              >
                                취소
                              </button>
                              <Button disabled={updateCommentMutation.isPending} type="submit">
                                댓글 저장
                              </Button>
                            </div>
                          </form>
                        ) : (
                          <p className="community-entry-copy">{comment.content}</p>
                        )}

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
                                      journalId: selectedJournal.id,
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
                      </article>
                    ))}
                    {selectedJournal.comments.length === 0 ? (
                      <div className="empty-state compact">
                        <p>아직 댓글이 없어요. 첫 번째 댓글을 남겨보세요.</p>
                      </div>
                    ) : null}
                  </div>
                </section>
              </div>
            )}
        </ModalOverlay>
      ) : null}
    </AppShell>
  );
}
