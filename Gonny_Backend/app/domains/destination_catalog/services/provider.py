from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.domains.destination_catalog.schemas import CatalogCityOption, CityPlaceCatalog
from app.domains.destination_catalog.services.repository import (
    DATA_DIR,
    DestinationCatalogRepository,
)


class PlaceCatalogProvider(ABC):
    @abstractmethod
    def get_city_catalog(
        self,
        *,
        continent: str | None,
        country: str | None,
        city: str | None,
    ) -> CityPlaceCatalog:
        raise NotImplementedError

    @abstractmethod
    def list_city_options(self) -> list[CatalogCityOption]:
        raise NotImplementedError


class LocalJsonPlaceCatalogProvider(PlaceCatalogProvider):
    def __init__(
        self,
        data_dir: Path | None = None,
        repository: DestinationCatalogRepository | None = None,
    ):
        self.repository = repository or DestinationCatalogRepository(data_dir=data_dir or DATA_DIR)

    def get_city_catalog(
        self,
        *,
        continent: str | None,
        country: str | None,
        city: str | None,
    ) -> CityPlaceCatalog:
        return self.repository.get_city_catalog(
            continent=continent,
            country=country,
            city=city,
        )

    def list_city_options(self) -> list[CatalogCityOption]:
        return self.repository.list_city_options()
