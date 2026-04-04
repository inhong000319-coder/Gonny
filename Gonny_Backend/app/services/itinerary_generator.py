import json
import logging
import re
from datetime import timedelta

from openai import OpenAI
from pydantic import ValidationError

from app.core.settings import settings
from app.schemas.generator import (
    GeneratedItineraryDay,
    GeneratedItineraryItem,
    GeneratedItineraryResponse,
)


TIME_SLOTS = ["morning", "afternoon", "evening"]
RAW_RESPONSE_LOG_LIMIT = 2000
JSON_SNIPPET_LOG_LIMIT = 1000

logger = logging.getLogger(__name__)


def _truncate_for_log(value, limit: int) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [truncated {len(text) - limit} chars]"


def build_itinerary_prompt(request_data):
    total_days = (request_data.end_date - request_data.start_date).days + 1
    total_days = max(total_days, 1)
    budget_value = request_data.budget

    if budget_value <= 100:
        budget_tier = "low"
        budget_guidance = (
            "This is a low budget trip. Prefer free or low-cost attractions, casual local eateries, "
            "street food, public viewpoints, markets, parks, and practical value-focused choices."
        )
    elif budget_value >= 300:
        budget_tier = "high"
        budget_guidance = (
            "This is a high budget trip. Prefer higher-quality dining, memorable experiences, scenic ambience, "
            "premium neighborhoods, stylish cafes, and places with stronger atmosphere and comfort."
        )
    else:
        budget_tier = "medium"
        budget_guidance = (
            "This is a medium budget trip. Balance cost and experience quality with a mix of worthwhile paid spots, "
            "reliable local restaurants, and comfortable but not overly expensive choices."
        )

    return (
        "You are a senior travel planner creating realistic, human-like itineraries.\n"
        "Your job is to produce a natural trip plan that feels thoughtfully arranged by a person, not a generic template.\n"
        "STRICTLY follow all rules.\n"
        "Do not ignore constraints.\n"
        "Failure to follow rules is not acceptable.\n"
        "\n"
        "[TRAVEL REQUEST]\n"
        f"Destination: {request_data.destination}\n"
        f"Travel dates: {request_data.start_date} to {request_data.end_date}\n"
        f"Total days: {total_days}\n"
        f"Budget amount: {budget_value}\n"
        f"Budget tier: {budget_tier}\n"
        f"Travel style: {request_data.travel_style}\n"
        f"Companion type: {request_data.companion_type}\n"
        "\n"
        "[ROLE]\n"
        "Plan each day with believable flow, distinct pacing, and practical transitions.\n"
        "Make the itinerary feel location-aware, mood-aware, budget-aware, and suitable for the travel companions.\n"
        "\n"
        "[OUTPUT CONSTRAINTS]\n"
        "Return JSON only.\n"
        "Do not include markdown.\n"
        "Do not include code fences.\n"
        "Do not include any explanation before or after the JSON.\n"
        "Return exactly one JSON object matching this shape:\n"
        "{\n"
        '  "days": [\n'
        "    {\n"
        '      "day_number": 1,\n'
        '      "items": [\n'
        "        {\n"
        '          "time_slot": "morning",\n'
        '          "place_name": "string",\n'
        '          "category": "string",\n'
        '          "notes": "string"\n'
        "        },\n"
        "        {\n"
        '          "time_slot": "afternoon",\n'
        '          "place_name": "string",\n'
        '          "category": "string",\n'
        '          "notes": "string"\n'
        "        },\n"
        "        {\n"
        '          "time_slot": "evening",\n'
        '          "place_name": "string",\n'
        '          "category": "string",\n'
        '          "notes": "string"\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "\n"
        "[STRUCTURE RULES]\n"
        f"The JSON must contain exactly {total_days} day objects.\n"
        f"Create day_number values from 1 to {total_days} with no gaps and no extras.\n"
        "Each day must contain exactly 3 items.\n"
        "Each day must include all three time slots exactly once, in this order: morning, afternoon, evening.\n"
        "time_slot must be one of: morning, afternoon, evening.\n"
        "place_name must be a specific place or a realistic place-style destination name, not a vague sentence.\n"
        "Do not use vague names like local cafe, city park, downtown restaurant, popular market, or nice viewpoint.\n"
        "Use recognizable or realistic place names.\n"
        "Prefer well-known districts, neighborhoods, landmarks, streets, markets, or venue-style names that feel specific to the destination.\n"
        "category should fit the activity, such as cafe, sightseeing, food, market, activity, nature, shopping, culture, or nightlife.\n"
        "\n"
        "[DAILY FLOW RULES]\n"
        "Morning should begin lightly: a calm walk, cafe, scenic spot, easy local exploration, or light sightseeing.\n"
        "Afternoon should contain the day's main activity, signature attraction, strongest meal plan, or core experience.\n"
        "Evening should close the day with dinner, sunset, drinks, a calm neighborhood stroll, river view, night market, or a relaxed final activity.\n"
        "Do not make every day feel equally intense.\n"
        "Avoid identical daily structure across the trip.\n"
        "Each day should feel slightly different in theme, mood, or focus.\n"
        "Avoid overpacking relax or family trips.\n"
        "Avoid unrealistic cross-city movement within a single day.\n"
        "Prefer same district or nearby areas per day.\n"
        "Group locations logically.\n"
        "Keep places within a believable area or route for the same day.\n"
        "Do not repeat the same place_name anywhere in the itinerary.\n"
        "Do not repeat the same type of recommendation mechanically every day.\n"
        "\n"
        "[BUDGET RULES]\n"
        f"{budget_guidance}\n"
        "If budget tier is low, favor free or low-cost attractions, casual local eateries, parks, viewpoints, markets, street food, and practical plans with good value.\n"
        "If budget tier is high, favor higher-quality dining, memorable experiences, scenic ambience, premium neighborhoods, refined cafes, and places with stronger atmosphere.\n"
        "If budget tier is medium, keep a balanced mix of value and quality.\n"
        "Budget influence must be visible in both place choice and note wording.\n"
        "\n"
        "[TRAVEL STYLE RULES]\n"
        "If travel_style is relax, keep pacing easy, include breathing room, scenic stops, and low-stress transitions.\n"
        "If travel_style is relax, make the day feel spacious rather than packed, and let the notes mention calm atmosphere or easy pacing when appropriate.\n"
        "If travel_style is foodie, make food experience a central part of the day and highlight what makes each food or cafe stop worth visiting.\n"
        "If travel_style is foodie, at least one item per day should clearly emphasize a meaningful food experience, local specialty, market food culture, or destination-specific dining appeal.\n"
        "If travel_style is activity, prioritize hands-on experiences, energetic attractions, and engaging daytime plans.\n"
        "If travel_style is activity, include at least one clearly experiential or participatory item each day rather than only passive sightseeing.\n"
        "If travel_style is sightseeing, prioritize iconic landmarks, neighborhoods, viewpoints, and culturally notable places.\n"
        "If travel_style is balanced, mix food, sights, atmosphere, and one meaningful activity without leaning too heavily into one category.\n"
        "\n"
        "[COMPANION RULES]\n"
        "If companion_type is solo, make the plan flexible, comfortable for independent movement, and suitable for exploring at one's own pace.\n"
        "If companion_type is friend, include lively shared experiences, trendy food spots, fun activity choices, and social energy.\n"
        "If companion_type is couple, include romantic atmosphere, scenic timing, intimate dining, and emotionally memorable settings.\n"
        "If companion_type is family, keep movement manageable, avoid exhausting pacing, and prefer comfortable, broadly enjoyable places.\n"
        "\n"
        "[NOTES RULES]\n"
        "Every notes field must sound natural and specific, not generic.\n"
        "Do not use repetitive phrases such as 'Recommended for relax travel' or similar templates.\n"
        "Do not use generic praise like good place, great for travelers, must-visit spot, nice atmosphere, or famous food without context.\n"
        "Each note must contain a DIFFERENT reason from the other notes in the itinerary.\n"
        "Avoid repeating sentence structure across notes.\n"
        "Make each note context-aware.\n"
        "Each note should briefly explain why the place fits that time of day.\n"
        "Each note should naturally reflect at least one of these: budget fit, travel style fit, companion fit, mood, pace, or route logic.\n"
        "Whenever possible, mention why this stop works in relation to the previous or next part of the day.\n"
        "Each note should help the itinerary feel human-curated, for example by mentioning atmosphere, timing, energy level, food value, scenic appeal, or convenience of moving to the next stop.\n"
        "Keep notes concise but meaningful.\n"
        "\n"
        "[QUALITY BAR]\n"
        "The final itinerary should feel realistic, varied, and thoughtfully sequenced.\n"
        "It should read like a plan made by a careful local travel planner.\n"
        "Return only the JSON object."
    )


def generate_mock_itinerary(request_data):
    total_days = (request_data.end_date - request_data.start_date).days + 1
    total_days = max(total_days, 1)

    days = []
    for index in range(total_days):
        current_date = request_data.start_date + timedelta(days=index)
        place_prefix = request_data.destination

        items = [
            GeneratedItineraryItem(
                time_slot="morning",
                place_name=f"{place_prefix} Central Spot {index + 1}",
                category="sightseeing",
                notes=(
                    f"Start day {index + 1} with a signature place in {request_data.destination}. "
                    f"Recommended for {request_data.travel_style} travel."
                ),
            ),
            GeneratedItineraryItem(
                time_slot="afternoon",
                place_name=f"{place_prefix} Local Experience {index + 1}",
                category="activity",
                notes=(
                    f"Plan an easy afternoon activity for a {request_data.companion_type} trip on {current_date}."
                ),
            ),
            GeneratedItineraryItem(
                time_slot="evening",
                place_name=f"{place_prefix} Dinner Place {index + 1}",
                category="food",
                notes=(
                    f"Keep the dinner budget aligned with the total budget of {request_data.budget}."
                ),
            ),
        ]

        days.append(GeneratedItineraryDay(day_number=index + 1, items=items))

    return GeneratedItineraryResponse(days=days)


def call_openai_itinerary(prompt: str):
    logger.info(
        "Starting OpenAI itinerary call. openai_api_key_configured=%s model=%s prompt_length=%s",
        bool(settings.openai_api_key),
        settings.openai_model,
        len(prompt),
    )

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    client = OpenAI()
    response = client.responses.create(
        model=settings.openai_model,
        input=prompt,
    )

    raw_text = getattr(response, "output_text", "")
    if raw_text:
        logger.info(
            "Received OpenAI response text. length=%s snippet=%s",
            len(raw_text),
            _truncate_for_log(raw_text, RAW_RESPONSE_LOG_LIMIT),
        )
        return raw_text

    raise ValueError("OpenAI response did not contain text output.")


def extract_json(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Response text is empty or not a string.")

    code_block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if code_block_match:
        extracted = code_block_match.group(1)
        logger.info(
            "extract_json succeeded from code block. length=%s snippet=%s",
            len(extracted),
            _truncate_for_log(extracted, JSON_SNIPPET_LOG_LIMIT),
        )
        return extracted

    start = text.find("{")
    if start == -1:
        logger.warning(
            "extract_json failed: JSON object start not found. response_snippet=%s",
            _truncate_for_log(text, RAW_RESPONSE_LOG_LIMIT),
        )
        raise ValueError("Could not find a JSON object start in the response.")

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                extracted = text[start:index + 1]
                logger.info(
                    "extract_json succeeded from brace scan. length=%s snippet=%s",
                    len(extracted),
                    _truncate_for_log(extracted, JSON_SNIPPET_LOG_LIMIT),
                )
                return extracted

    logger.warning(
        "extract_json failed: complete JSON object not found. response_snippet=%s",
        _truncate_for_log(text, RAW_RESPONSE_LOG_LIMIT),
    )
    raise ValueError("Could not extract a complete JSON object from the response.")


def parse_generated_itinerary(raw_text_or_data):
    if isinstance(raw_text_or_data, GeneratedItineraryResponse):
        parsed = GeneratedItineraryResponse.model_validate(raw_text_or_data)
        logger.info(
            "parse_generated_itinerary received GeneratedItineraryResponse. days=%s total_items=%s",
            len(parsed.days),
            sum(len(day.items) for day in parsed.days),
        )
        return parsed

    if isinstance(raw_text_or_data, dict):
        parsed = GeneratedItineraryResponse.model_validate(raw_text_or_data)
        logger.info(
            "parse_generated_itinerary received dict. days=%s total_items=%s",
            len(parsed.days),
            sum(len(day.items) for day in parsed.days),
        )
        return parsed

    if isinstance(raw_text_or_data, str):
        extracted_json = extract_json(raw_text_or_data)
        parsed_data = json.loads(extracted_json)
        parsed = GeneratedItineraryResponse.model_validate(parsed_data)
        logger.info(
            "parse_generated_itinerary succeeded from string. days=%s total_items=%s",
            len(parsed.days),
            sum(len(day.items) for day in parsed.days),
        )
        return parsed

    raise ValueError("Unsupported generated itinerary format.")


def validate_generated_itinerary(data):
    validated = GeneratedItineraryResponse.model_validate(data)

    if not validated.days:
        raise ValueError("Generated itinerary must include at least one day.")

    for day in validated.days:
        if day.day_number < 1:
            raise ValueError("day_number must be greater than or equal to 1.")

        if not day.items:
            raise ValueError("Each day must include at least one itinerary item.")

        seen_slots = set()
        for item in day.items:
            if item.time_slot not in TIME_SLOTS:
                raise ValueError(f"Invalid time_slot: {item.time_slot}")
            if item.time_slot in seen_slots:
                raise ValueError(f"Duplicate time_slot in day {day.day_number}: {item.time_slot}")
            seen_slots.add(item.time_slot)

    logger.info(
        "validate_generated_itinerary passed. days=%s total_items=%s",
        len(validated.days),
        sum(len(day.items) for day in validated.days),
    )
    return validated


def generate_itinerary(request_data):
    prompt = build_itinerary_prompt(request_data)
    total_days = (request_data.end_date - request_data.start_date).days + 1
    total_days = max(total_days, 1)

    logger.info(
        "generate_itinerary started. destination=%s total_days=%s budget=%s travel_style=%s companion_type=%s openai_api_key_configured=%s",
        request_data.destination,
        total_days,
        request_data.budget,
        request_data.travel_style,
        request_data.companion_type,
        bool(settings.openai_api_key),
    )

    try:
        raw_response = call_openai_itinerary(prompt)
    except Exception as exc:
        logger.exception(
            "OpenAI itinerary generation failed before parsing. destination=%s error=%s",
            request_data.destination,
            exc,
        )
        logger.warning(
            "Falling back to mock itinerary. destination=%s stage=openai_call reason=%s",
            request_data.destination,
            exc,
        )
        return generate_mock_itinerary(request_data)

    try:
        parsed = parse_generated_itinerary(raw_response)
    except (ValueError, ValidationError, json.JSONDecodeError) as exc:
        logger.exception(
            "Failed to parse generated itinerary. destination=%s error=%s raw_response_snippet=%s",
            request_data.destination,
            exc,
            _truncate_for_log(raw_response, RAW_RESPONSE_LOG_LIMIT),
        )
        logger.warning(
            "Falling back to mock itinerary. destination=%s stage=parse reason=%s",
            request_data.destination,
            exc,
        )
        return generate_mock_itinerary(request_data)

    try:
        validated = validate_generated_itinerary(parsed)
    except (ValueError, ValidationError) as exc:
        logger.exception(
            "Generated itinerary failed validation. destination=%s error=%s",
            request_data.destination,
            exc,
        )
        logger.warning(
            "Falling back to mock itinerary. destination=%s stage=validate reason=%s",
            request_data.destination,
            exc,
        )
        return generate_mock_itinerary(request_data)

    logger.info(
        "generate_itinerary completed successfully. destination=%s days=%s total_items=%s",
        request_data.destination,
        len(validated.days),
        sum(len(day.items) for day in validated.days),
    )

    try:
        return validated
    except (ValueError, ValidationError, json.JSONDecodeError) as exc:
        logger.exception(
            "Unexpected itinerary generation failure after validation. destination=%s error=%s",
            request_data.destination,
            exc,
        )
        logger.warning(
            "Falling back to mock itinerary. destination=%s stage=unexpected reason=%s",
            request_data.destination,
            exc,
        )
        return generate_mock_itinerary(request_data)
