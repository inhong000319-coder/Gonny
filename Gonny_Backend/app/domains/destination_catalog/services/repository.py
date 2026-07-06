from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException, status

from app.domains.destination_catalog.schemas import (
    CatalogCityOption,
    CityPlaceCatalog,
    CreateDestinationRequest,
    DestinationSummary,
    PlaceData,
)


DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "destinations"
ACTIVITY_CATEGORIES = {"activity", "theme_park", "local_experience"}


class DestinationCatalogRepository:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR

    def load_catalogs(self) -> list[CityPlaceCatalog]:
        catalogs: list[CityPlaceCatalog] = []
        for file_path in sorted(self.data_dir.glob("*.json")):
            with file_path.open("r", encoding="utf-8") as file:
                raw_data = json.load(file)
            catalogs.append(CityPlaceCatalog.model_validate(raw_data))
        return catalogs

    def get_city_catalog(
        self,
        *,
        continent: str | None,
        country: str | None,
        city: str | None,
    ) -> CityPlaceCatalog:
        catalogs = self.load_catalogs()

        normalized_continent = (continent or "").strip().lower()
        normalized_country = (country or "").strip().lower()
        normalized_city = (city or "").strip().lower()

        if normalized_city:
            for catalog in catalogs:
                aliases = {catalog.city.lower(), *[alias.lower() for alias in catalog.aliases]}
                if normalized_city in aliases:
                    return catalog

        if normalized_country:
            for catalog in catalogs:
                if catalog.country.lower() == normalized_country:
                    return catalog

        if normalized_continent:
            for catalog in catalogs:
                if catalog.continent.lower() == normalized_continent:
                    return catalog

        if catalogs:
            return catalogs[0]

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No local destination catalog is available.",
        )

    def list_city_options(self) -> list[CatalogCityOption]:
        return [
            CatalogCityOption(
                continent=catalog.continent,
                country=catalog.country,
                city=catalog.city,
                aliases=catalog.aliases,
            )
            for catalog in self.load_catalogs()
        ]

    def list_destination_summaries(self) -> list[DestinationSummary]:
        destinations: list[DestinationSummary] = []
        for path in sorted(self.data_dir.glob("*.json")):
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
                        1 for place in places if set(place.get("category", [])) & ACTIVITY_CATEGORIES
                    ),
                )
            )
        return destinations

    def create_destination(self, request: CreateDestinationRequest) -> CityPlaceCatalog:
        continent = self._normalize_code(request.continent, field_name="Continent code")
        country = self._normalize_code(request.country, field_name="Country code")
        city = self._normalize_code(request.city, field_name="City code")

        path = self.data_dir / f"{city}.json"
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
        return self._save_destination(path, payload)

    def get_destination(self, city: str) -> CityPlaceCatalog:
        _, payload = self._load_destination(city)
        return CityPlaceCatalog.model_validate(payload)

    def create_place(self, city: str, request: PlaceData) -> CityPlaceCatalog:
        path, payload = self._load_destination(city)
        places = payload.get("places", [])
        self._validate_unique_place_fields(
            places,
            place_id=request.id,
            place_name=request.name,
        )
        places.append(request.model_dump())
        payload["places"] = places
        return self._save_destination(path, payload)

    def update_place(self, city: str, place_id: str, request: PlaceData) -> CityPlaceCatalog:
        path, payload = self._load_destination(city)
        places = payload.get("places", [])
        self._validate_unique_place_fields(
            places,
            place_id=request.id,
            place_name=request.name,
            ignore_place_id=place_id,
        )
        normalized_place_id = place_id.strip().lower()
        for index, place in enumerate(places):
            if str(place.get("id", "")).strip().lower() == normalized_place_id:
                places[index] = request.model_dump()
                payload["places"] = places
                return self._save_destination(path, payload)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found.")

    def update_place_active(self, city: str, place_id: str, is_active: bool) -> CityPlaceCatalog:
        path, payload = self._load_destination(city)
        places = payload.get("places", [])
        normalized_place_id = place_id.strip().lower()
        for place in places:
            if str(place.get("id", "")).strip().lower() == normalized_place_id:
                place["is_active"] = is_active
                payload["places"] = places
                return self._save_destination(path, payload)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found.")

    def _normalize_code(self, value: str, *, field_name: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} is required.",
            )
        return normalized

    def _validate_unique_place_fields(
        self,
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

    def _destination_path(self, city: str) -> Path:
        normalized = self._normalize_code(city, field_name="City code")
        path = self.data_dir / f"{normalized}.json"
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found.")
        return path

    def _load_destination(self, city: str) -> tuple[Path, dict]:
        path = self._destination_path(city)
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return path, payload

    def _save_destination(self, path: Path, payload: dict) -> CityPlaceCatalog:
        with path.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
        return CityPlaceCatalog.model_validate(payload)


destination_catalog_repository = DestinationCatalogRepository()
