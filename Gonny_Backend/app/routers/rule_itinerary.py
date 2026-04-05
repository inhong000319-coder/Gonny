from fastapi import APIRouter

from app.schemas.rule_itinerary import (
    RuleItineraryCatalogResponse,
    RuleItineraryRequest,
    RuleItineraryResponse,
)
from app.services.rule_itinerary_service import rule_itinerary_service


router = APIRouter(prefix="/rule-itinerary", tags=["rule-itinerary"])


@router.get("/options", response_model=RuleItineraryCatalogResponse)
def list_rule_itinerary_options():
    return RuleItineraryCatalogResponse(cities=rule_itinerary_service.list_catalog_options())


@router.post("/generate", response_model=RuleItineraryResponse)
def generate_rule_itinerary(request: RuleItineraryRequest):
    return rule_itinerary_service.generate(request)
