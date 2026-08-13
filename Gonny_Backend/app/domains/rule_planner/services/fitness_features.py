from __future__ import annotations

from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest


def build_feature_tags(
    *,
    concepts: list[str],
    style: str,
    companion_type: str,
    budget_band: str,
    activity_type: list[str],
    mood: list[str],
    mood_evening_override: list[str],
    visual_feature: list[str],
    budget_level: list[str],
    suitable_for: list[str],
    mobility: list[str],
) -> list[str]:
    """Build the prefixed tag vocabulary shared by training and inference.

    Prefixes keep same-spelled values from different fields (e.g. request
    budget_band="low" vs place budget_level containing "low") from colliding
    once everything is flattened into a single MultiLabelBinarizer space.
    """
    tags: list[str] = []
    tags.extend(f"concept:{value}" for value in concepts)
    tags.append(f"style:{style}")
    tags.append(f"companion:{companion_type}")
    tags.append(f"budget_band:{budget_band}")
    tags.extend(f"activity_type:{value}" for value in activity_type)
    tags.extend(f"mood:{value}" for value in mood)
    tags.extend(f"mood_evening_override:{value}" for value in mood_evening_override)
    tags.extend(f"visual_feature:{value}" for value in visual_feature)
    tags.extend(f"budget_level:{value}" for value in budget_level)
    tags.extend(f"suitable_for:{value}" for value in suitable_for)
    tags.extend(f"mobility:{value}" for value in mobility)
    return tags


def build_tags_for_place_and_request(place: PlaceData, request: NormalizedRuleRequest) -> list[str]:
    return build_feature_tags(
        concepts=list(request.concepts),
        style=request.style,
        companion_type=request.companion_type,
        budget_band=request.budget_band,
        activity_type=place.activity_type,
        mood=place.mood,
        mood_evening_override=place.mood_evening_override,
        visual_feature=place.visual_feature,
        budget_level=place.budget_level,
        suitable_for=place.suitable_for,
        mobility=place.mobility,
    )
