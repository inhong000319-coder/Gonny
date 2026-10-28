from fastapi import APIRouter

from app.domains.rule_planner.schemas import (
    RuleItineraryCatalogResponse,
    RuleItineraryRecalculateRequest,
    RuleItineraryRequest,
    RuleItineraryResponse,
    RuleTransportComparisonResponse,
)
from app.domains.rule_planner.services.service import rule_itinerary_service


router = APIRouter(prefix="/rule-itinerary", tags=["rule-itinerary"])


@router.get("/options", response_model=RuleItineraryCatalogResponse)
def list_rule_itinerary_options():
    return RuleItineraryCatalogResponse(cities=rule_itinerary_service.list_catalog_options())


@router.post("/generate", response_model=RuleItineraryResponse)
def generate_rule_itinerary(request: RuleItineraryRequest):
    return rule_itinerary_service.generate(request)


@router.post("/compare-transport", response_model=RuleTransportComparisonResponse)
def compare_rule_itinerary_transport(request: RuleItineraryRequest):
    return rule_itinerary_service.compare_transport(request)


@router.post("/recalculate", response_model=RuleItineraryResponse)
def recalculate_rule_itinerary(request: RuleItineraryRecalculateRequest):
    return rule_itinerary_service.recalculate(request)
