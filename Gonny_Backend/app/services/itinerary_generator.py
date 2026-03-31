import json
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


def build_itinerary_prompt(request_data):
    return (
        "You are an itinerary planning assistant.\n"
        "Generate a travel itinerary in JSON only.\n"
        "Return exactly this shape:\n"
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
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "Rules:\n"
        "- time_slot must be one of: morning, afternoon, evening\n"
        "- Each day should have practical items in chronological order\n"
        "- Do not include markdown or explanations\n"
        "- Do not wrap JSON in code fences\n"
        "- Keep recommendations aligned with destination, budget, travel style, and companion type\n"
        f"Destination: {request_data.destination}\n"
        f"Travel dates: {request_data.start_date} to {request_data.end_date}\n"
        f"Budget: {request_data.budget}\n"
        f"Travel style: {request_data.travel_style}\n"
        f"Companion type: {request_data.companion_type}"
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
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    client = OpenAI()
    response = client.responses.create(
        model=settings.openai_model,
        input=prompt,
    )

    raw_text = getattr(response, "output_text", "")
    if raw_text:
        return raw_text

    raise ValueError("OpenAI response did not contain text output.")


def parse_generated_itinerary(raw_text_or_data):
    if isinstance(raw_text_or_data, GeneratedItineraryResponse):
        return raw_text_or_data

    if isinstance(raw_text_or_data, dict):
        return GeneratedItineraryResponse.model_validate(raw_text_or_data)

    if isinstance(raw_text_or_data, str):
        parsed_data = json.loads(raw_text_or_data)
        return GeneratedItineraryResponse.model_validate(parsed_data)

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

    return validated


def generate_itinerary(request_data):
    prompt = build_itinerary_prompt(request_data)

    try:
        raw_response = call_openai_itinerary(prompt)
        parsed = parse_generated_itinerary(raw_response)
        validated = validate_generated_itinerary(parsed)
        return validated
    except (ValueError, ValidationError, json.JSONDecodeError):
        return generate_mock_itinerary(request_data)
