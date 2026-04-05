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
    total_places: int
    active_places: int
    activity_places: int


class DestinationListResponse(BaseModel):
    destinations: list[DestinationSummary]


class UpdatePlaceActiveRequest(BaseModel):
    is_active: bool


class CreatePlaceRequest(PlaceData):
    model_config = ConfigDict(str_strip_whitespace=True)


def _destination_path(city: str) -> Path:
    normalized = city.strip().lower()
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


@router.get("/{city}", response_model=CityPlaceCatalog)
def get_destination(city: str):
    _, payload = _load_destination(city)
    return CityPlaceCatalog.model_validate(payload)


@router.post("/{city}/places", response_model=CityPlaceCatalog, status_code=status.HTTP_201_CREATED)
def create_place(city: str, request: CreatePlaceRequest):
    path, payload = _load_destination(city)
    places = payload.get("places", [])
    if any(str(place.get("id", "")).strip().lower() == request.id.lower() for place in places):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Place id already exists.")
    places.append(request.model_dump())
    payload["places"] = places
    return _save_destination(path, payload)


@router.put("/{city}/places/{place_id}", response_model=CityPlaceCatalog)
def update_place(city: str, place_id: str, request: PlaceData):
    path, payload = _load_destination(city)
    places = payload.get("places", [])
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
