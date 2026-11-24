from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException, status

from app.domains.destination_catalog.schemas import (
    ALTERNATE_TIER,
    CatalogCityOption,
    CityPlaceCatalog,
    CreateDestinationRequest,
    DestinationSummary,
    PlaceData,
)


DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "destinations"
ACTIVITY_CATEGORIES = {"activity", "theme_park", "local_experience"}
VISIBLE_CITY_CODES = {"seoul", "busan", "jeju"}

# 하루 일정의 슬롯 수(아침/오후/저녁 고정) - #139. 일정 성향별로 슬롯 수가
# 달라질 수 있어 compute_recommended_max_days의 인자로 뺐고, 지금은 이
# 기본값 하나로만 호출한다.
DEFAULT_DAY_SLOT_COUNT = 3


def compute_recommended_max_days(activity_candidate_count: int, slot_count: int = DEFAULT_DAY_SLOT_COUNT) -> int:
    """장소를 가득 채워 추천할 수 있는 최대 일수의 근사치(#139).

    같은 장소를 한 일정에 한 번만 쓰는 규칙(RuleItineraryService.
    _build_items) 때문에, 활동 후보 장소가 slot_count만큼씩 다 쓰이고
    나면 그 뒤로는 활동 장소가 바닥나 빈 날이 생긴다. activity_candidate_
    count // slot_count(정수 나눗셈)로 슬롯이 완전히 채워지는 날 수만
    센다 - 마지막에 slot_count보다 적게 남는 장소는 그 날을 다 채우지
    못하므로 포함하지 않는다(예: 25곳 // 3 = 8, 1곳이 남아도 9일째는
    세지 않음).

    종일 코스(PlaceData.full_day_recommended) 장소는 실제로는 슬롯 3개를
    한 번에 다 쓰므로, 이 값은 정확한 날짜 수가 아니라 근사치다.

    slot_count<=0이면 나눗셈이 의미가 없으므로 0을 돌려준다.
    """
    if slot_count <= 0:
        return 0
    return activity_candidate_count // slot_count


class DestinationCatalogRepository:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR

    def load_catalogs(self, *, visible_only: bool = False) -> list[CityPlaceCatalog]:
        catalogs: list[CityPlaceCatalog] = []
        for file_path in sorted(self.data_dir.glob("*.json")):
            with file_path.open("r", encoding="utf-8") as file:
                raw_data = json.load(file)
            catalog = CityPlaceCatalog.model_validate(raw_data)
            if visible_only and not self._is_visible_catalog(catalog.city):
                continue
            catalogs.append(catalog)
        return catalogs

    def get_city_catalog(
        self,
        *,
        continent: str | None,
        country: str | None,
        city: str | None,
        visible_only: bool = False,
    ) -> CityPlaceCatalog:
        catalogs = self.load_catalogs(visible_only=visible_only)

        normalized_continent = (continent or "").strip().lower()
        normalized_country = (country or "").strip().lower()
        normalized_city = (city or "").strip().lower()

        if normalized_city:
            for catalog in catalogs:
                aliases = {catalog.city.lower(), *[alias.lower() for alias in catalog.aliases]}
                if normalized_city in aliases:
                    return catalog
            if visible_only:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Destination is currently unavailable.",
                )

        if normalized_country:
            for catalog in catalogs:
                if catalog.country.lower() == normalized_country:
                    return catalog
            if visible_only:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Destination is currently unavailable.",
                )

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

    def list_city_options(self, *, visible_only: bool = False) -> list[CatalogCityOption]:
        return [
            CatalogCityOption(
                continent=catalog.continent,
                country=catalog.country,
                city=catalog.city,
                aliases=catalog.aliases,
                recommended_max_days=compute_recommended_max_days(
                    sum(
                        1
                        for place in catalog.places
                        if place.is_active and place.is_activity_candidate and place.mvp_tier != ALTERNATE_TIER
                    )
                ),
            )
            for catalog in self.load_catalogs(visible_only=visible_only)
        ]

    def list_destination_summaries(self, *, visible_only: bool = False) -> list[DestinationSummary]:
        destinations: list[DestinationSummary] = []
        for path in sorted(self.data_dir.glob("*.json")):
            if visible_only and not self._is_visible_catalog(path.stem):
                continue
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
                        if set(place.get("activity_type", [])) & ACTIVITY_CATEGORIES
                        or "액티비티" in place.get("activity_type", [])
                    ),
                )
            )
        return destinations

    def _is_visible_catalog(self, city: str) -> bool:
        return city.strip().lower() in VISIBLE_CITY_CODES

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
