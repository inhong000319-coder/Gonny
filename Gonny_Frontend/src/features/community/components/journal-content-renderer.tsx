import { TravelJournalContentBlock } from "../types/community";

function resolveImageUrl(url: string | null | undefined) {
  if (!url) {
    return "";
  }
  return url.startsWith("http") ? url : `http://localhost:8000${url}`;
}

function buildCropImageStyle(block: TravelJournalContentBlock) {
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

type Props = {
  blocks: TravelJournalContentBlock[];
  fallbackText?: string | null;
};

export function JournalContentRenderer({ blocks, fallbackText }: Props) {
  const visibleBlocks =
    blocks.length > 0
      ? blocks
      : fallbackText?.trim()
        ? [{ id: "fallback-text", type: "text" as const, text: fallbackText }]
        : [];

  return (
    <div className="journal-doc-surface">
      {visibleBlocks.map((block) => {
        if (block.type === "text") {
          return (
            <div className="journal-doc-text" key={block.id}>
              <p className="community-entry-copy">{block.text}</p>
            </div>
          );
        }

        const imageUrl = resolveImageUrl(block.url);
        const textItems = block.text_items ?? [];
        const emojiItems = block.emoji_items ?? [];
        const drawItems = block.draw_items ?? [];

        return (
          <figure
            className={`journal-doc-image-wrap layout-${block.layout ?? "large"}`}
            key={block.id}
            style={{ width: `${block.width_percent ?? 100}%` }}
          >
            <div className={`journal-image-frame aspect-${block.aspect_ratio ?? "landscape"}`}>
              <img
                alt={block.caption || "다이어리 사진"}
                className="journal-image-thumb"
                src={imageUrl}
                style={buildCropImageStyle(block)}
              />
              {drawItems.length ? (
                <svg className="journal-draw-layer" viewBox="0 0 100 100" preserveAspectRatio="none">
                  {drawItems.map((item) => (
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
              {textItems.map((item) => (
                <div
                  className="journal-image-overlay-text"
                  key={item.id}
                  style={{
                    left: `${item.x}%`,
                    top: `${item.y}%`,
                    bottom: "auto",
                    right: "auto",
                    transform: `translate(-50%, -50%) rotate(${item.rotation ?? 0}deg)`,
                    fontSize: `${item.size ?? 18}px`,
                    whiteSpace: "pre-wrap",
                    color: item.color ?? "#ffffff",
                  }}
                >
                  {item.text}
                </div>
              ))}
              {emojiItems.map((item) => (
                <div
                  className="journal-image-overlay-emoji"
                  key={item.id}
                  style={{
                    left: `${item.x}%`,
                    top: `${item.y}%`,
                    right: "auto",
                    transform: `translate(-50%, -50%) rotate(${item.rotation ?? 0}deg)`,
                    fontSize: `${item.size ?? 34}px`,
                    minWidth: "unset",
                    minHeight: "unset",
                    padding: "8px 10px",
                    color: item.color ?? "#ffffff",
                  }}
                >
                  {item.emoji}
                </div>
              ))}
            </div>
            {block.caption ? <figcaption className="journal-image-caption">{block.caption}</figcaption> : null}
          </figure>
        );
      })}
    </div>
  );
}
