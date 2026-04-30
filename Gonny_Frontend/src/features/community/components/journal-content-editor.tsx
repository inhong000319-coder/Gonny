import { ChangeEvent, PointerEvent, useEffect, useMemo, useRef, useState } from "react";
import { TravelJournalContentBlock } from "../types/community";
import { ModalOverlay } from "../../../shared/components/ui/modal-overlay";

type OverlayTextItem = NonNullable<TravelJournalContentBlock["text_items"]>[number];
type OverlayEmojiItem = NonNullable<TravelJournalContentBlock["emoji_items"]>[number];
type DrawItem = NonNullable<TravelJournalContentBlock["draw_items"]>[number];

export type JournalEditorBlock = TravelJournalContentBlock & {
  file?: File | null;
  localPreviewUrl?: string | null;
};

type Props = {
  blocks: JournalEditorBlock[];
  imageCount: number;
  maxImages: number;
  onChange: (blocks: JournalEditorBlock[]) => void;
};

type StudioState = {
  open: boolean;
  blockId: string | null;
  history: JournalEditorBlock[];
  future: JournalEditorBlock[];
};

type ActiveTool = "select" | "crop" | "draw" | "erase";

type SelectedTarget =
  | { kind: "text"; id: string }
  | { kind: "emoji"; id: string }
  | { kind: "draw"; id: string }
  | null;

type CropRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

const aspectRatioOptions = [
  { value: "square", label: "정사각형" },
  { value: "portrait", label: "세로" },
  { value: "landscape", label: "가로" },
  { value: "story", label: "스토리" },
] as const;

const presetColors = ["#111827", "#ffffff", "#ef4444", "#facc15"] as const;

function createId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function createTextBlock(text = ""): JournalEditorBlock {
  return {
    id: createId("text"),
    type: "text",
    text,
  };
}

function createImageBlock(file: File): JournalEditorBlock {
  return {
    id: createId("image"),
    type: "image",
    file,
    localPreviewUrl: URL.createObjectURL(file),
    url: null,
    caption: "",
    layout: "full",
    aspect_ratio: "landscape",
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
  };
}

function resolvePreviewUrl(block: JournalEditorBlock) {
  const source = block.localPreviewUrl || block.url || "";
  if (!source) {
    return "";
  }
  return source.startsWith("blob:") || source.startsWith("http") ? source : `http://localhost:8000${source}`;
}

function cloneBlock(block: JournalEditorBlock): JournalEditorBlock {
  return JSON.parse(JSON.stringify(block)) as JournalEditorBlock;
}

function getCropRect(block: JournalEditorBlock): CropRect {
  return {
    left: block.crop_left ?? 0,
    top: block.crop_top ?? 0,
    width: block.crop_width ?? 100,
    height: block.crop_height ?? 100,
  };
}

function buildCropImageStyle(block: JournalEditorBlock) {
  const cropLeft = block.crop_left ?? 0;
  const cropTop = block.crop_top ?? 0;
  const cropWidth = Math.max(1, block.crop_width ?? 100);
  const cropHeight = Math.max(1, block.crop_height ?? 100);

  return {
    position: "absolute" as const,
    width: `${10000 / cropWidth}%`,
    height: `${10000 / cropHeight}%`,
    left: `-${(cropLeft / cropWidth) * 100}%`,
    top: `-${(cropTop / cropHeight) * 100}%`,
    maxWidth: "none",
  };
}

function eraseDrawItemsAtPoint(drawItems: DrawItem[], point: { x: number; y: number }, radius: number) {
  const nextItems: DrawItem[] = [];

  drawItems.forEach((item) => {
    let currentSegment: Array<{ x: number; y: number }> = [];

    item.points.forEach((linePoint) => {
      const dx = linePoint.x - point.x;
      const dy = linePoint.y - point.y;
      const shouldErase = Math.sqrt(dx * dx + dy * dy) <= radius;

      if (shouldErase) {
        if (currentSegment.length > 1) {
          nextItems.push({
            ...item,
            id: createId("draw"),
            points: currentSegment,
          });
        }
        currentSegment = [];
        return;
      }

      currentSegment = [...currentSegment, linePoint];
    });

    if (currentSegment.length > 1) {
      nextItems.push({
        ...item,
        id: createId("draw"),
        points: currentSegment,
      });
    }
  });

  return nextItems;
}

export function JournalContentEditor({ blocks, imageCount, maxImages, onChange }: Props) {
  const [studioState, setStudioState] = useState<StudioState>({
    open: false,
    blockId: null,
    history: [],
    future: [],
  });

  const studioBlock = useMemo(
    () => blocks.find((block) => block.id === studioState.blockId && block.type === "image") ?? null,
    [blocks, studioState.blockId],
  );

  const replaceBlocks = (nextBlocks: JournalEditorBlock[]) => onChange(nextBlocks);

  const updateBlock = (blockId: string, patch: Partial<JournalEditorBlock>) => {
    replaceBlocks(blocks.map((block) => (block.id === blockId ? { ...block, ...patch } : block)));
  };

  const insertTextBlock = (afterIndex?: number) => {
    const nextBlock = createTextBlock();
    if (afterIndex === undefined) {
      replaceBlocks([...blocks, nextBlock]);
      return;
    }
    const nextBlocks = [...blocks];
    nextBlocks.splice(afterIndex + 1, 0, nextBlock);
    replaceBlocks(nextBlocks);
  };

  const insertImageBlocks = (files: FileList | File[], afterIndex?: number) => {
    const accepted = Array.from(files)
      .slice(0, Math.max(0, maxImages - imageCount))
      .map((file) => createImageBlock(file));
    if (!accepted.length) {
      return;
    }
    if (afterIndex === undefined) {
      replaceBlocks([...blocks, ...accepted]);
      return;
    }
    const nextBlocks = [...blocks];
    nextBlocks.splice(afterIndex + 1, 0, ...accepted);
    replaceBlocks(nextBlocks);
  };

  const removeBlock = (blockId: string) => replaceBlocks(blocks.filter((block) => block.id !== blockId));

  const handleImageInsert =
    (afterIndex?: number) =>
    (event: ChangeEvent<HTMLInputElement>) => {
      if (event.target.files?.length) {
        insertImageBlocks(event.target.files, afterIndex);
      }
      event.target.value = "";
    };

  const openStudio = (blockId: string) => {
    const imageBlock = blocks.find((block) => block.id === blockId && block.type === "image");
    if (!imageBlock) {
      return;
    }
    setStudioState({
      open: true,
      blockId,
      history: [cloneBlock(imageBlock)],
      future: [],
    });
  };

  const closeStudio = () => {
    setStudioState({ open: false, blockId: null, history: [], future: [] });
  };

  const updateStudioBlock = (patch: Partial<JournalEditorBlock>, track = true) => {
    if (!studioBlock) {
      return;
    }
    const nextBlock = { ...studioBlock, ...patch };
    updateBlock(studioBlock.id, nextBlock);
    if (track) {
      setStudioState((prev) => ({
        ...prev,
        history: [...prev.history, cloneBlock(nextBlock)].slice(-80),
        future: [],
      }));
    }
  };

  const undoStudio = () => {
    if (!studioBlock || studioState.history.length < 2) {
      return;
    }
    const nextHistory = studioState.history.slice(0, -1);
    const previous = nextHistory[nextHistory.length - 1];
    updateBlock(studioBlock.id, previous);
    setStudioState((prev) => ({
      ...prev,
      history: nextHistory,
      future: [cloneBlock(studioBlock), ...prev.future].slice(0, 80),
    }));
  };

  const redoStudio = () => {
    if (!studioBlock || studioState.future.length === 0) {
      return;
    }
    const [nextBlock, ...restFuture] = studioState.future;
    updateBlock(studioBlock.id, nextBlock);
    setStudioState((prev) => ({
      ...prev,
      history: [...prev.history, cloneBlock(nextBlock)].slice(-80),
      future: restFuture,
    }));
  };

  return (
    <>
      <div className="journal-editor-toolbar">
        <div className="journal-editor-toolbar-copy">
          <strong>다이어리 본문 편집</strong>
          <span>문단과 사진을 한 흐름으로 적고, 사진은 편집기에서 바로 자르기와 꾸미기를 할 수 있어요.</span>
        </div>
        <div className="journal-editor-toolbar-actions">
          <button className="button secondary" onClick={() => insertTextBlock()} type="button">
            문단 추가
          </button>
          <label className="button primary">
            사진 올리기
            <input accept="image/*" hidden multiple onChange={handleImageInsert()} type="file" />
          </label>
          <span className="chip">사진 {imageCount}/{maxImages}</span>
        </div>
      </div>

      <div className="journal-doc-editor">
        {blocks.map((block, index) => (
          <div className="journal-doc-node" key={block.id}>
            {block.type === "text" ? (
              <textarea
                className="journal-doc-textarea"
                placeholder="여행에서 느낀 분위기와 기억하고 싶은 순간을 자연스럽게 적어보세요."
                rows={Math.max(4, (block.text?.split("\n").length ?? 1) + 1)}
                value={block.text ?? ""}
                onChange={(event) => updateBlock(block.id, { text: event.target.value })}
              />
            ) : (
              <div className="journal-doc-image-node" style={{ width: `${block.width_percent ?? 100}%` }}>
                <PreviewImage block={block} />
                {block.caption ? <div className="journal-image-caption">{block.caption}</div> : null}
                <div className="journal-doc-image-actions">
                  <button className="button secondary" onClick={() => openStudio(block.id)} type="button">
                    이미지 편집하기
                  </button>
                  <button className="button ghost" onClick={() => removeBlock(block.id)} type="button">
                    사진 제거
                  </button>
                </div>
              </div>
            )}

            <div className="journal-doc-inline-actions">
              <button className="button ghost" onClick={() => insertTextBlock(index)} type="button">
                아래에 문단 추가
              </button>
              <label className="button ghost">
                아래에 사진 추가
                <input accept="image/*" hidden multiple onChange={handleImageInsert(index)} type="file" />
              </label>
              {block.type === "text" ? (
                <button className="button ghost" onClick={() => removeBlock(block.id)} type="button">
                  문단 제거
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      {studioState.open && studioBlock ? (
        <ImageStudioModal
          block={studioBlock}
          canRedo={studioState.future.length > 0}
          canUndo={studioState.history.length > 1}
          onBlockChange={(patch, track) => updateStudioBlock(patch, track)}
          onClose={closeStudio}
          onRedo={redoStudio}
          onUndo={undoStudio}
        />
      ) : null}
    </>
  );
}

function PreviewImage({ block }: { block: JournalEditorBlock }) {
  const imageUrl = resolvePreviewUrl(block);

  return (
    <div className={`journal-image-frame aspect-${block.aspect_ratio ?? "landscape"}`}>
      <img alt={block.caption || "다이어리 사진"} className="journal-image-thumb" src={imageUrl} style={buildCropImageStyle(block)} />
      {(block.draw_items ?? []).length ? (
        <svg className="journal-draw-layer" preserveAspectRatio="none" viewBox="0 0 100 100">
          {(block.draw_items ?? []).map((item) => (
            <polyline
              key={item.id}
              fill="none"
              points={item.points.map((point) => `${point.x},${point.y}`).join(" ")}
              stroke={item.color}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={(item.size / 100) * 4}
            />
          ))}
        </svg>
      ) : null}
      {(block.text_items ?? []).map((item) => (
        <div
          className="journal-image-overlay-text"
          key={item.id}
          style={{
            left: `${item.x}%`,
            top: `${item.y}%`,
            transform: `translate(-50%, -50%) rotate(${item.rotation ?? 0}deg)`,
            fontSize: `${item.size ?? 18}px`,
            color: item.color ?? "#ffffff",
          }}
        >
          {item.text}
        </div>
      ))}
      {(block.emoji_items ?? []).map((item) => (
        <div
          className="journal-image-overlay-emoji"
          key={item.id}
          style={{
            left: `${item.x}%`,
            top: `${item.y}%`,
            transform: `translate(-50%, -50%) rotate(${item.rotation ?? 0}deg)`,
            fontSize: `${item.size ?? 34}px`,
            color: item.color ?? "#ffffff",
          }}
        >
          {item.emoji}
        </div>
      ))}
    </div>
  );
}

type ImageStudioModalProps = {
  block: JournalEditorBlock;
  canUndo: boolean;
  canRedo: boolean;
  onClose: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onBlockChange: (patch: Partial<JournalEditorBlock>, track?: boolean) => void;
};

function ImageStudioModal({ block, canUndo, canRedo, onClose, onUndo, onRedo, onBlockChange }: ImageStudioModalProps) {
  const previewRef = useRef<HTMLDivElement | null>(null);
  const [activeTool, setActiveTool] = useState<ActiveTool>("select");
  const [selectedTarget, setSelectedTarget] = useState<SelectedTarget>(null);
  const [drawColor, setDrawColor] = useState("#111827");
  const [drawSize, setDrawSize] = useState(18);
  const [showCustomColor, setShowCustomColor] = useState(false);
  const [localCrop, setLocalCrop] = useState<CropRect>(getCropRect(block));
  const [draftDrawPoints, setDraftDrawPoints] = useState<Array<{ x: number; y: number }>>([]);
  const imageUrl = resolvePreviewUrl(block);

  useEffect(() => {
    setActiveTool("select");
    setSelectedTarget(null);
    setLocalCrop(getCropRect(block));
    setDraftDrawPoints([]);
  }, [block.id]);

  const selectedText =
    selectedTarget?.kind === "text" ? (block.text_items ?? []).find((item) => item.id === selectedTarget.id) ?? null : null;
  const selectedEmoji =
    selectedTarget?.kind === "emoji" ? (block.emoji_items ?? []).find((item) => item.id === selectedTarget.id) ?? null : null;
  const selectedDraw =
    selectedTarget?.kind === "draw" ? (block.draw_items ?? []).find((item) => item.id === selectedTarget.id) ?? null : null;

  const currentColor = selectedText?.color ?? selectedEmoji?.color ?? selectedDraw?.color ?? drawColor;

  const updateSelectedText = (patch: Partial<OverlayTextItem>) => {
    if (!selectedText) {
      return;
    }
    onBlockChange({
      text_items: (block.text_items ?? []).map((item) => (item.id === selectedText.id ? { ...item, ...patch } : item)),
    });
  };

  const updateSelectedEmoji = (patch: Partial<OverlayEmojiItem>) => {
    if (!selectedEmoji) {
      return;
    }
    onBlockChange({
      emoji_items: (block.emoji_items ?? []).map((item) => (item.id === selectedEmoji.id ? { ...item, ...patch } : item)),
    });
  };

  const updateSelectedDraw = (patch: Partial<DrawItem>) => {
    if (!selectedDraw) {
      return;
    }
    onBlockChange({
      draw_items: (block.draw_items ?? []).map((item) => (item.id === selectedDraw.id ? { ...item, ...patch } : item)),
    });
  };

  const applyColor = (color: string) => {
    if (activeTool === "draw" || activeTool === "erase") {
      setDrawColor(color);
      return;
    }
    if (selectedText) {
      updateSelectedText({ color });
      return;
    }
    if (selectedEmoji) {
      updateSelectedEmoji({ color });
      return;
    }
    if (selectedDraw) {
      updateSelectedDraw({ color });
      return;
    }
    setDrawColor(color);
  };

  const deleteSelected = () => {
    if (selectedText) {
      onBlockChange({ text_items: (block.text_items ?? []).filter((item) => item.id !== selectedText.id) });
      setSelectedTarget(null);
      return;
    }
    if (selectedEmoji) {
      onBlockChange({ emoji_items: (block.emoji_items ?? []).filter((item) => item.id !== selectedEmoji.id) });
      setSelectedTarget(null);
      return;
    }
    if (selectedDraw) {
      onBlockChange({ draw_items: (block.draw_items ?? []).filter((item) => item.id !== selectedDraw.id) });
      setSelectedTarget(null);
    }
  };

  const setTool = (tool: ActiveTool) => {
    setDraftDrawPoints([]);
    setSelectedTarget((prev) => (tool === "select" ? prev : null));
    if (tool === "crop") {
      setLocalCrop(getCropRect(block));
    }
    setActiveTool((prev) => (prev === tool ? "select" : tool));
  };

  const startStickerDrag = (
    event: PointerEvent<HTMLDivElement>,
    target: Extract<SelectedTarget, { kind: "text" | "emoji" }>,
  ) => {
    if (activeTool !== "select") {
      return;
    }

    const frame = previewRef.current;
    if (!frame) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    setSelectedTarget(target);

    const element = event.currentTarget;
    const rect = frame.getBoundingClientRect();
    const startX = event.clientX;
    const startY = event.clientY;
    const items = target.kind === "text" ? block.text_items ?? [] : block.emoji_items ?? [];
    const current = items.find((item) => item.id === target.id);
    if (!current) {
      return;
    }

    const initialX = current.x;
    const initialY = current.y;
    let lastX = initialX;
    let lastY = initialY;
    element.setPointerCapture(event.pointerId);
    document.body.style.userSelect = "none";

    const move = (moveEvent: globalThis.PointerEvent) => {
      moveEvent.preventDefault();
      lastX = clamp(initialX + (((moveEvent.clientX - startX) / rect.width) * 100), 5, 95);
      lastY = clamp(initialY + (((moveEvent.clientY - startY) / rect.height) * 100), 5, 95);
      element.style.left = `${lastX}%`;
      element.style.top = `${lastY}%`;
    };

    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      document.body.style.userSelect = "";
      if (target.kind === "text") {
        onBlockChange({
          text_items: (block.text_items ?? []).map((item) =>
            item.id === target.id ? { ...item, x: lastX, y: lastY } : item,
          ),
        });
      } else {
        onBlockChange({
          emoji_items: (block.emoji_items ?? []).map((item) =>
            item.id === target.id ? { ...item, x: lastX, y: lastY } : item,
          ),
        });
      }
    };

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  const startCropInteraction = (
    event: PointerEvent<HTMLDivElement | HTMLButtonElement>,
    mode: "move" | "nw" | "ne" | "sw" | "se",
  ) => {
    if (activeTool !== "crop" || !previewRef.current) {
      return;
    }

    event.stopPropagation();
    const rect = previewRef.current.getBoundingClientRect();
    const startX = event.clientX;
    const startY = event.clientY;
    const initial = { ...localCrop };
    event.currentTarget.setPointerCapture(event.pointerId);

    const move = (moveEvent: globalThis.PointerEvent) => {
      const deltaX = ((moveEvent.clientX - startX) / rect.width) * 100;
      const deltaY = ((moveEvent.clientY - startY) / rect.height) * 100;
      let next = { ...initial };

      if (mode === "move") {
        next.left = clamp(initial.left + deltaX, 0, 100 - initial.width);
        next.top = clamp(initial.top + deltaY, 0, 100 - initial.height);
      }

      if (mode === "nw" || mode === "sw") {
        const newLeft = clamp(initial.left + deltaX, 0, initial.left + initial.width - 5);
        next.width = initial.width + (initial.left - newLeft);
        next.left = newLeft;
      }

      if (mode === "ne" || mode === "se") {
        const newWidth = clamp(initial.width + deltaX, 5, 100 - initial.left);
        next.width = newWidth;
      }

      if (mode === "nw" || mode === "ne") {
        const newTop = clamp(initial.top + deltaY, 0, initial.top + initial.height - 5);
        next.height = initial.height + (initial.top - newTop);
        next.top = newTop;
      }

      if (mode === "sw" || mode === "se") {
        const newHeight = clamp(initial.height + deltaY, 5, 100 - initial.top);
        next.height = newHeight;
      }

      next.left = clamp(next.left, 0, 100 - next.width);
      next.top = clamp(next.top, 0, 100 - next.height);
      setLocalCrop(next);
    };

    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  const applyCrop = () => {
    onBlockChange({
      crop_left: Number(localCrop.left.toFixed(2)),
      crop_top: Number(localCrop.top.toFixed(2)),
      crop_width: Number(localCrop.width.toFixed(2)),
      crop_height: Number(localCrop.height.toFixed(2)),
    });
    setActiveTool("select");
  };

  const resetCrop = () => {
    const full = { left: 0, top: 0, width: 100, height: 100 };
    setLocalCrop(full);
    onBlockChange({
      crop_left: full.left,
      crop_top: full.top,
      crop_width: full.width,
      crop_height: full.height,
    });
    setActiveTool("select");
  };

  const getPointFromEvent = (clientX: number, clientY: number) => {
    const rect = previewRef.current?.getBoundingClientRect();
    if (!rect) {
      return null;
    }
    return {
      x: clamp(((clientX - rect.left) / rect.width) * 100, 0, 100),
      y: clamp(((clientY - rect.top) / rect.height) * 100, 0, 100),
    };
  };

  const startDrawing = (event: PointerEvent<SVGSVGElement>) => {
    if ((activeTool !== "draw" && activeTool !== "erase") || !previewRef.current) {
      return;
    }

    if (activeTool === "erase") {
      event.preventDefault();
      event.stopPropagation();
      let workingItems = (block.draw_items ?? []).map((item) => ({
        ...item,
        points: item.points.map((point) => ({ ...point })),
      }));

      const eraseAtPoint = (clientX: number, clientY: number) => {
        const point = getPointFromEvent(clientX, clientY);
        if (!point) {
          return;
        }
        const threshold = Math.max(1.2, drawSize / 3.6);
        workingItems = eraseDrawItemsAtPoint(workingItems, point, threshold);
        onBlockChange({ draw_items: workingItems }, false);
      };

      eraseAtPoint(event.clientX, event.clientY);
      event.currentTarget.setPointerCapture(event.pointerId);

      const move = (moveEvent: globalThis.PointerEvent) => {
        eraseAtPoint(moveEvent.clientX, moveEvent.clientY);
      };

      const up = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
        onBlockChange({ draw_items: workingItems }, true);
        if (
          selectedTarget?.kind === "draw" &&
          !workingItems.some((item) => item.id === selectedTarget.id)
        ) {
          setSelectedTarget(null);
        }
      };

      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up);
      return;
    }

    const firstPoint = getPointFromEvent(event.clientX, event.clientY);
    if (!firstPoint) {
      return;
    }

    event.currentTarget.setPointerCapture(event.pointerId);
    const nextPoints = [firstPoint];
    setDraftDrawPoints(nextPoints);

    const move = (moveEvent: globalThis.PointerEvent) => {
      const nextPoint = getPointFromEvent(moveEvent.clientX, moveEvent.clientY);
      if (!nextPoint) {
        return;
      }
      nextPoints.push(nextPoint);
      setDraftDrawPoints([...nextPoints]);
    };

    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);

      if (nextPoints.length > 1) {
        const newDraw: DrawItem = {
          id: createId("draw"),
          color: drawColor,
          size: drawSize,
          points: nextPoints,
        };
        onBlockChange({ draw_items: [...(block.draw_items ?? []), newDraw] });
        setSelectedTarget({ kind: "draw", id: newDraw.id });
      }
      setDraftDrawPoints([]);
    };

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  const handleDrawLineClick = (drawId: string) => {
    if (activeTool === "erase") {
      return;
    }
    if (activeTool === "select") {
      setSelectedTarget({ kind: "draw", id: drawId });
    }
  };

  return (
    <ModalOverlay className="memory-modal memory-modal-wide" onClose={onClose}>
        <div className="section-header">
          <div>
            <h2 className="section-title">이미지 편집하기</h2>
            <p className="section-subtitle">실제 크롭 박스로 자르고, 텍스트·이모티콘·그리기를 바로 확인하면서 수정해보세요.</p>
          </div>
          <div className="row">
            <button className="button secondary" disabled={!canUndo} onClick={onUndo} type="button">
              ←
            </button>
            <button className="button secondary" disabled={!canRedo} onClick={onRedo} type="button">
              →
            </button>
            <button className="button ghost" onClick={onClose} type="button">
              닫기
            </button>
          </div>
        </div>

        <div className="journal-studio-layout">
          <div className="journal-studio-preview-panel">
            <div className="journal-studio-preview-wrap" style={{ width: `${block.width_percent ?? 100}%` }}>
              <div className={`journal-image-frame aspect-${block.aspect_ratio ?? "landscape"} journal-studio-frame`} ref={previewRef}>
                {activeTool === "crop" ? (
                  <>
                    <img alt={block.caption || "편집 이미지"} className="journal-image-thumb journal-image-edit-base" src={imageUrl} />
                    <div className="journal-crop-overlay">
                      <div
                        className="journal-crop-box"
                        style={{
                          left: `${localCrop.left}%`,
                          top: `${localCrop.top}%`,
                          width: `${localCrop.width}%`,
                          height: `${localCrop.height}%`,
                        }}
                        onPointerDown={(event) => startCropInteraction(event, "move")}
                      >
                        <button className="journal-crop-handle nw" onPointerDown={(event) => startCropInteraction(event, "nw")} type="button" />
                        <button className="journal-crop-handle ne" onPointerDown={(event) => startCropInteraction(event, "ne")} type="button" />
                        <button className="journal-crop-handle sw" onPointerDown={(event) => startCropInteraction(event, "sw")} type="button" />
                        <button className="journal-crop-handle se" onPointerDown={(event) => startCropInteraction(event, "se")} type="button" />
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <img alt={block.caption || "편집 이미지"} className="journal-image-thumb" src={imageUrl} style={buildCropImageStyle(block)} />
                    {(block.draw_items ?? []).length ? (
                      <svg
                        className="journal-draw-layer"
                        preserveAspectRatio="none"
                        style={{ pointerEvents: activeTool === "select" || activeTool === "erase" ? "auto" : "none" }}
                        viewBox="0 0 100 100"
                      >
                        {(block.draw_items ?? []).map((item) => (
                          <polyline
                            key={item.id}
                            fill="none"
                            points={item.points.map((point) => `${point.x},${point.y}`).join(" ")}
                            stroke={item.color}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeOpacity={selectedTarget?.kind === "draw" && selectedTarget.id === item.id ? 1 : 0.92}
                            strokeWidth={(item.size / 100) * 4}
                            onClick={() => handleDrawLineClick(item.id)}
                          />
                        ))}
                        {draftDrawPoints.length ? (
                          <polyline
                            fill="none"
                            points={draftDrawPoints.map((point) => `${point.x},${point.y}`).join(" ")}
                            stroke={drawColor}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={(drawSize / 100) * 4}
                          />
                        ) : null}
                      </svg>
                    ) : null}

                    {!block.draw_items?.length && draftDrawPoints.length ? (
                      <svg className="journal-draw-layer" preserveAspectRatio="none" viewBox="0 0 100 100">
                        <polyline
                          fill="none"
                          points={draftDrawPoints.map((point) => `${point.x},${point.y}`).join(" ")}
                          stroke={drawColor}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={(drawSize / 100) * 4}
                        />
                      </svg>
                    ) : null}

                    {(block.text_items ?? []).map((item) => (
                      <div
                        className={`journal-image-overlay-text journal-studio-sticker ${selectedTarget?.kind === "text" && selectedTarget.id === item.id ? "selected" : ""}`}
                        draggable={false}
                        key={item.id}
                        style={{
                          left: `${item.x}%`,
                          top: `${item.y}%`,
                          transform: `translate(-50%, -50%) rotate(${item.rotation ?? 0}deg)`,
                          fontSize: `${item.size ?? 18}px`,
                          color: item.color ?? "#ffffff",
                        }}
                        onPointerDown={(event) => startStickerDrag(event, { kind: "text", id: item.id })}
                      >
                        {item.text}
                      </div>
                    ))}

                    {(block.emoji_items ?? []).map((item) => (
                      <div
                        className={`journal-image-overlay-emoji journal-studio-sticker ${selectedTarget?.kind === "emoji" && selectedTarget.id === item.id ? "selected" : ""}`}
                        draggable={false}
                        key={item.id}
                        style={{
                          left: `${item.x}%`,
                          top: `${item.y}%`,
                          transform: `translate(-50%, -50%) rotate(${item.rotation ?? 0}deg)`,
                          fontSize: `${item.size ?? 34}px`,
                          color: item.color ?? "#ffffff",
                        }}
                        onPointerDown={(event) => startStickerDrag(event, { kind: "emoji", id: item.id })}
                      >
                        {item.emoji}
                      </div>
                    ))}

                    {(activeTool === "draw" || activeTool === "erase") ? (
                      <svg
                        className={`journal-draw-layer journal-draw-layer-edit ${activeTool === "erase" ? "erase" : ""}`}
                        preserveAspectRatio="none"
                        viewBox="0 0 100 100"
                        onPointerDown={startDrawing}
                      />
                    ) : null}
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="journal-studio-controls">
            <div className="journal-studio-toolbar">
              <label className="button secondary">
                사진 교체
                <input
                  accept="image/*"
                  hidden
                  type="file"
                  onChange={(event) => {
                    const nextFile = event.target.files?.[0];
                    if (nextFile) {
                      onBlockChange({
                        file: nextFile,
                        localPreviewUrl: URL.createObjectURL(nextFile),
                        url: null,
                        crop_left: 0,
                        crop_top: 0,
                        crop_width: 100,
                        crop_height: 100,
                      });
                    }
                    event.target.value = "";
                  }}
                />
              </label>
              <button
                className="button secondary"
                onClick={() =>
                  onBlockChange({
                    text_items: [...(block.text_items ?? []), { id: createId("text-item"), text: "텍스트", x: 50, y: 50, size: 20, rotation: 0, color: "#ffffff" }],
                  })
                }
                type="button"
              >
                텍스트 추가
              </button>
              <button
                className="button secondary"
                onClick={() =>
                  onBlockChange({
                    emoji_items: [...(block.emoji_items ?? []), { id: createId("emoji"), emoji: "💛", x: 50, y: 50, size: 34, rotation: 0, color: "#ffffff" }],
                  })
                }
                type="button"
              >
                이모티콘 추가
              </button>
              <button className={`button ${activeTool === "crop" ? "primary" : "secondary"}`} onClick={() => setTool("crop")} type="button">
                자르기 모드
              </button>
              <button className={`button ${activeTool === "draw" ? "primary" : "secondary"}`} onClick={() => setTool("draw")} type="button">
                자유그리기
              </button>
              <button className={`button ${activeTool === "erase" ? "primary" : "secondary"}`} onClick={() => setTool("erase")} type="button">
                지우개
              </button>
            </div>

            <div className="journal-studio-grid">
              <label className="field">
                <span>프레임 비율</span>
                <select
                  className="input"
                  value={block.aspect_ratio ?? "landscape"}
                  onChange={(event) => onBlockChange({ aspect_ratio: event.target.value as JournalEditorBlock["aspect_ratio"] })}
                >
                  {aspectRatioOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>사진 설명</span>
                <input className="input" placeholder="사진 설명을 적어보세요." value={block.caption ?? ""} onChange={(event) => onBlockChange({ caption: event.target.value })} />
              </label>
            </div>

            <div className="journal-color-palette">
              {presetColors.map((color) => (
                <button
                  key={color}
                  className={`journal-color-swatch ${currentColor === color ? "selected" : ""}`}
                  style={{ background: color, borderColor: color === "#ffffff" ? "rgba(148,163,184,0.7)" : color }}
                  onClick={() => applyColor(color)}
                  type="button"
                />
              ))}
              <button className="button ghost" onClick={() => setShowCustomColor((prev) => !prev)} type="button">
                RGB 선택
              </button>
              {showCustomColor ? <input className="input input-color" type="color" value={currentColor} onChange={(event) => applyColor(event.target.value)} /> : null}
            </div>

            {activeTool === "crop" ? (
              <div className="journal-studio-overlay-editor">
                <div className="journal-studio-overlay-row">
                  <strong>자르기</strong>
                  <div className="row">
                    <button className="button ghost" onClick={() => setTool("crop")} type="button">
                      취소
                    </button>
                    <button className="button secondary" onClick={resetCrop} type="button">
                      전체로 복원
                    </button>
                    <button className="button primary" onClick={applyCrop} type="button">
                      자르기 적용
                    </button>
                  </div>
                </div>
                <p className="section-subtitle">모서리를 끌어서 영역을 줄이고, 박스 안을 끌어서 위치를 옮길 수 있어요.</p>
              </div>
            ) : null}

            {(activeTool === "draw" || activeTool === "erase" || selectedDraw) ? (
              <div className="journal-studio-overlay-editor">
                <div className="journal-studio-overlay-row">
                  <strong>{activeTool === "erase" ? "지우개" : "그리기"}</strong>
                  <div className="row">
                    {selectedDraw ? (
                      <button className="button ghost" onClick={deleteSelected} type="button">
                        선택 선 삭제
                      </button>
                    ) : null}
                    <button className="button ghost" onClick={() => onBlockChange({ draw_items: [] })} type="button">
                      전체 지우기
                    </button>
                  </div>
                </div>
                <label className="field">
                  <span>
                    {activeTool === "draw"
                      ? "기본 선 굵기"
                      : activeTool === "erase"
                        ? "지우개 굵기"
                        : "선 굵기"}
                  </span>
                  <input
                    className="input"
                    max={40}
                    min={1}
                    type="range"
                    value={activeTool === "draw" || activeTool === "erase" ? drawSize : (selectedDraw?.size ?? drawSize)}
                    onChange={(event) => {
                      const nextSize = Number(event.target.value);
                      if (activeTool === "draw" || activeTool === "erase") {
                        setDrawSize(nextSize);
                        return;
                      }
                      if (selectedDraw) {
                        updateSelectedDraw({ size: nextSize });
                      }
                    }}
                  />
                </label>
              </div>
            ) : null}

            {selectedText ? (
              <div className="journal-studio-overlay-editor">
                <div className="journal-studio-overlay-row">
                  <input className="input" value={selectedText.text} onChange={(event) => updateSelectedText({ text: event.target.value })} />
                  <button className="button ghost" onClick={deleteSelected} type="button">
                    삭제
                  </button>
                </div>
                <div className="journal-studio-overlay-sliders">
                  <label className="field">
                    <span>크기</span>
                    <input className="input" max={72} min={12} type="range" value={selectedText.size ?? 18} onChange={(event) => updateSelectedText({ size: Number(event.target.value) })} />
                  </label>
                  <label className="field">
                    <span>각도</span>
                    <input className="input" max={180} min={-180} type="range" value={selectedText.rotation ?? 0} onChange={(event) => updateSelectedText({ rotation: Number(event.target.value) })} />
                  </label>
                </div>
              </div>
            ) : null}

            {selectedEmoji ? (
              <div className="journal-studio-overlay-editor">
                <div className="journal-studio-overlay-row">
                  <input className="input" maxLength={4} value={selectedEmoji.emoji} onChange={(event) => updateSelectedEmoji({ emoji: event.target.value })} />
                  <button className="button ghost" onClick={deleteSelected} type="button">
                    삭제
                  </button>
                </div>
                <div className="journal-studio-overlay-sliders">
                  <label className="field">
                    <span>크기</span>
                    <input className="input" max={96} min={18} type="range" value={selectedEmoji.size ?? 34} onChange={(event) => updateSelectedEmoji({ size: Number(event.target.value) })} />
                  </label>
                  <label className="field">
                    <span>각도</span>
                    <input className="input" max={180} min={-180} type="range" value={selectedEmoji.rotation ?? 0} onChange={(event) => updateSelectedEmoji({ rotation: Number(event.target.value) })} />
                  </label>
                </div>
              </div>
            ) : null}
          </div>
        </div>
    </ModalOverlay>
  );
}
