from abc import ABC, abstractmethod

from app.schemas.place_catalog import CityPlaceCatalog
from app.schemas.rule_itinerary import CatalogCityOption


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
