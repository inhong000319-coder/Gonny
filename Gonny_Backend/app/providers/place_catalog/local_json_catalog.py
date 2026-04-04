import json
from pathlib import Path

from fastapi import HTTPException, status

from app.providers.place_catalog.base import PlaceCatalogProvider
from app.schemas.place_catalog import CityPlaceCatalog
from app.schemas.rule_itinerary import CatalogCityOption


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "destinations"


class LocalJsonPlaceCatalogProvider(PlaceCatalogProvider):
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR

    def _load_catalogs(self) -> list[CityPlaceCatalog]:
        catalogs: list[CityPlaceCatalog] = []
        for file_path in sorted(self.data_dir.glob("*.json")):
            with open(file_path, "r", encoding="utf-8") as file:
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
        catalogs = self._load_catalogs()

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
            for catalog in self._load_catalogs()
        ]
