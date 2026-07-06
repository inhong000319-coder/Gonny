from __future__ import annotations

from app.models.travel_journal import TravelJournalReaction


def build_recommendation_count(reactions: list[TravelJournalReaction]) -> int:
    return sum(max(reaction.count, 0) for reaction in reactions)


def normalize_travel_journal_content_blocks(
    content_blocks: list[dict] | list | None,
    diary_text: str,
    image_urls: list[str] | None,
) -> list[dict]:
    normalized_blocks: list[dict] = []
    raw_blocks = content_blocks or []
    for index, raw_block in enumerate(raw_blocks):
        block_data = raw_block if isinstance(raw_block, dict) else raw_block.model_dump()
        block_type = block_data.get("type")
        block_id = block_data.get("id") or f"block-{index + 1}"
        if block_type == "text":
            text_value = (block_data.get("text") or "").strip()
            if not text_value:
                continue
            normalized_blocks.append(
                {
                    "id": block_id,
                    "type": "text",
                    "text": text_value,
                }
            )
        elif block_type == "image":
            image_url = (block_data.get("url") or "").strip()
            if not image_url:
                continue
            overlay_text = (block_data.get("overlay_text") or "").strip()
            emoji_value = (block_data.get("emoji") or "").strip()
            text_items = block_data.get("text_items") or []
            emoji_items = block_data.get("emoji_items") or []
            draw_items = block_data.get("draw_items") or []
            if overlay_text and not text_items:
                text_items = [{"id": f"{block_id}-text-1", "text": overlay_text, "x": 50, "y": 82}]
            if emoji_value and not emoji_items:
                emoji_items = [{"id": f"{block_id}-emoji-1", "emoji": emoji_value, "x": 84, "y": 18, "size": 42}]
            normalized_blocks.append(
                {
                    "id": block_id,
                    "type": "image",
                    "url": image_url,
                    "caption": (block_data.get("caption") or "").strip() or None,
                    "layout": block_data.get("layout") or "large",
                    "aspect_ratio": block_data.get("aspect_ratio") or "landscape",
                    "overlay_text": overlay_text or None,
                    "emoji": emoji_value or None,
                    "crop_x": max(0, min(100, int(block_data.get("crop_x", 50) or 50))),
                    "crop_y": max(0, min(100, int(block_data.get("crop_y", 50) or 50))),
                    "crop_left": max(0.0, min(99.0, float(block_data.get("crop_left", 0.0) or 0.0))),
                    "crop_top": max(0.0, min(99.0, float(block_data.get("crop_top", 0.0) or 0.0))),
                    "crop_width": max(1.0, min(100.0, float(block_data.get("crop_width", 100.0) or 100.0))),
                    "crop_height": max(1.0, min(100.0, float(block_data.get("crop_height", 100.0) or 100.0))),
                    "width_percent": max(30, min(100, int(block_data.get("width_percent", 100) or 100))),
                    "zoom": max(1.0, min(4.0, float(block_data.get("zoom", 1.0) or 1.0))),
                    "offset_x": max(-100.0, min(100.0, float(block_data.get("offset_x", 0.0) or 0.0))),
                    "offset_y": max(-100.0, min(100.0, float(block_data.get("offset_y", 0.0) or 0.0))),
                    "text_items": [item for item in text_items if isinstance(item, dict)],
                    "emoji_items": [item for item in emoji_items if isinstance(item, dict)],
                    "draw_items": [item for item in draw_items if isinstance(item, dict)],
                }
            )

    if normalized_blocks:
        return normalized_blocks

    fallback_blocks: list[dict] = []
    if diary_text.strip():
        fallback_blocks.append(
            {
                "id": "block-text-1",
                "type": "text",
                "text": diary_text.strip(),
            }
        )
    for index, image_url in enumerate(image_urls or [], start=1):
        if not image_url:
            continue
        fallback_blocks.append(
            {
                "id": f"block-image-{index}",
                "type": "image",
                "url": image_url,
                "caption": None,
                "layout": "large",
                "aspect_ratio": "landscape",
                "overlay_text": None,
                "emoji": None,
                "crop_x": 50,
                "crop_y": 50,
                "crop_left": 0.0,
                "crop_top": 0.0,
                "crop_width": 100.0,
                "crop_height": 100.0,
                "width_percent": 100,
                "zoom": 1.0,
                "offset_x": 0.0,
                "offset_y": 0.0,
                "text_items": [],
                "emoji_items": [],
                "draw_items": [],
            }
        )
    return fallback_blocks


def build_travel_journal_summary(content_blocks: list[dict], fallback_text: str) -> str:
    text_fragments = [(block.get("text") or "").strip() for block in content_blocks if block.get("type") == "text"]
    summary_source = "\n\n".join(fragment for fragment in text_fragments if fragment).strip() or fallback_text.strip()
    if len(summary_source) <= 600:
        return summary_source
    return f"{summary_source[:597].rstrip()}..."


def collect_travel_journal_image_urls(content_blocks: list[dict], fallback_urls: list[str] | None) -> list[str]:
    urls = [(block.get("url") or "").strip() for block in content_blocks if block.get("type") == "image"]
    normalized_urls = [url for url in urls if url]
    return normalized_urls or [url for url in (fallback_urls or []) if url]
