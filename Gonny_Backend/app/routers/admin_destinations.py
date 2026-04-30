from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.providers.place_catalog.local_json_catalog import DATA_DIR
from app.schemas.place_catalog import CityPlaceCatalog, PlaceData


router = APIRouter(prefix="/admin/destinations", tags=["admin-destinations"])


class DestinationSummary(BaseModel):
    continent: str
    country: str
    city: str
    continent_label: str | None = None
    country_label: str | None = None
    city_label: str | None = None
    total_places: int
    active_places: int
    activity_places: int


class DestinationListResponse(BaseModel):
    destinations: list[DestinationSummary]


class UpdatePlaceActiveRequest(BaseModel):
    is_active: bool


class CreatePlaceRequest(PlaceData):
    model_config = ConfigDict(str_strip_whitespace=True)


class CreateDestinationRequest(BaseModel):
    continent: str
    country: str
    city: str
    continent_label: str | None = None
    country_label: str | None = None
    city_label: str | None = None
    aliases: list[str] = Field(default_factory=list)
    default_days: int = Field(default=3, ge=1, le=14)

    model_config = ConfigDict(str_strip_whitespace=True)


def _normalize_code(value: str, *, field_name: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required.",
        )
    return normalized


def _validate_unique_place_fields(
    places: list[dict],
    *,
    place_id: str,
    place_name: str,
    ignore_place_id: str | None = None,
) -> None:
    normalized_place_id = place_id.strip().lower()
    normalized_place_name = place_name.strip().lower()
    normalized_ignore_id = ignore_place_id.strip().lower() if ignore_place_id else None

    for place in places:
        current_id = str(place.get("id", "")).strip().lower()
        current_name = str(place.get("name", "")).strip().lower()

        if normalized_ignore_id and current_id == normalized_ignore_id:
            continue

        if current_id == normalized_place_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Place id already exists.")
        if current_name == normalized_place_name:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Place name already exists.")


def _destination_path(city: str) -> Path:
    normalized = _normalize_code(city, field_name="City code")
    path = DATA_DIR / f"{normalized}.json"
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found.")
    return path


def _load_destination(city: str) -> tuple[Path, dict]:
    path = _destination_path(city)
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return path, payload


def _save_destination(path: Path, payload: dict) -> CityPlaceCatalog:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return CityPlaceCatalog.model_validate(payload)


@router.get("", response_model=DestinationListResponse)
def list_destinations():
    destinations: list[DestinationSummary] = []
    for path in sorted(DATA_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        places = payload.get("places", [])
        destinations.append(
            DestinationSummary(
                continent=payload.get("continent", ""),
                country=payload.get("country", ""),
                city=payload.get("city", path.stem),
                continent_label=payload.get("continent_label"),
                country_label=payload.get("country_label"),
                city_label=payload.get("city_label"),
                total_places=len(places),
                active_places=sum(1 for place in places if place.get("is_active", True)),
                activity_places=sum(
                    1
                    for place in places
                    if set(place.get("category", [])) & {"activity", "theme_park", "local_experience"}
                ),
            )
        )
    return DestinationListResponse(destinations=destinations)


@router.post("", response_model=CityPlaceCatalog, status_code=status.HTTP_201_CREATED)
def create_destination(request: CreateDestinationRequest):
    continent = _normalize_code(request.continent, field_name="Continent code")
    country = _normalize_code(request.country, field_name="Country code")
    city = _normalize_code(request.city, field_name="City code")

    path = DATA_DIR / f"{city}.json"
    if path.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Destination already exists.")

    payload = {
        "continent": continent,
        "country": country,
        "city": city,
        "continent_label": request.continent_label or None,
        "country_label": request.country_label or None,
        "city_label": request.city_label or None,
        "aliases": sorted({alias.strip() for alias in request.aliases if alias.strip()}),
        "default_days": request.default_days,
        "places": [],
    }
    return _save_destination(path, payload)


@router.get("/{city}", response_model=CityPlaceCatalog)
def get_destination(city: str):
    _, payload = _load_destination(city)
    return CityPlaceCatalog.model_validate(payload)


@router.post("/{city}/places", response_model=CityPlaceCatalog, status_code=status.HTTP_201_CREATED)
def create_place(city: str, request: CreatePlaceRequest):
    path, payload = _load_destination(city)
    places = payload.get("places", [])
    _validate_unique_place_fields(
        places,
        place_id=request.id,
        place_name=request.name,
    )
    places.append(request.model_dump())
    payload["places"] = places
    return _save_destination(path, payload)


@router.put("/{city}/places/{place_id}", response_model=CityPlaceCatalog)
def update_place(city: str, place_id: str, request: PlaceData):
    path, payload = _load_destination(city)
    places = payload.get("places", [])
    _validate_unique_place_fields(
        places,
        place_id=request.id,
        place_name=request.name,
        ignore_place_id=place_id,
    )
    for index, place in enumerate(places):
        if str(place.get("id", "")).strip().lower() == place_id.strip().lower():
            places[index] = request.model_dump()
            payload["places"] = places
            return _save_destination(path, payload)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found.")


@router.patch("/{city}/places/{place_id}/active", response_model=CityPlaceCatalog)
def update_place_active(city: str, place_id: str, request: UpdatePlaceActiveRequest):
    path, payload = _load_destination(city)
    places = payload.get("places", [])
    for place in places:
        if str(place.get("id", "")).strip().lower() == place_id.strip().lower():
            place["is_active"] = request.is_active
            payload["places"] = places
            return _save_destination(path, payload)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found.")
