from __future__ import annotations

from fastapi import APIRouter, status

from app.domains.destination_catalog.schemas import (
    CityPlaceCatalog,
    CreateDestinationRequest,
    CreatePlaceRequest,
    DestinationListResponse,
    PlaceData,
    UpdatePlaceActiveRequest,
)
from app.domains.destination_catalog.services.repository import destination_catalog_repository


router = APIRouter(prefix="/admin/destinations", tags=["admin-destinations"])


@router.get("", response_model=DestinationListResponse)
def list_destinations() -> DestinationListResponse:
    return DestinationListResponse(
        destinations=destination_catalog_repository.list_destination_summaries()
    )


@router.post("", response_model=CityPlaceCatalog, status_code=status.HTTP_201_CREATED)
def create_destination(request: CreateDestinationRequest) -> CityPlaceCatalog:
    return destination_catalog_repository.create_destination(request)


@router.get("/{city}", response_model=CityPlaceCatalog)
def get_destination(city: str) -> CityPlaceCatalog:
    return destination_catalog_repository.get_destination(city)


@router.post("/{city}/places", response_model=CityPlaceCatalog, status_code=status.HTTP_201_CREATED)
def create_place(city: str, request: CreatePlaceRequest) -> CityPlaceCatalog:
    return destination_catalog_repository.create_place(city, request)


@router.put("/{city}/places/{place_id}", response_model=CityPlaceCatalog)
def update_place(city: str, place_id: str, request: PlaceData) -> CityPlaceCatalog:
    return destination_catalog_repository.update_place(city, place_id, request)


@router.patch("/{city}/places/{place_id}/active", response_model=CityPlaceCatalog)
def update_place_active(
    city: str,
    place_id: str,
    request: UpdatePlaceActiveRequest,
) -> CityPlaceCatalog:
    return destination_catalog_repository.update_place_active(city, place_id, request.is_active)
