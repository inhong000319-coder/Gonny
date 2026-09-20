from fastapi import APIRouter

from .schemas import SeasonalFeedResponse
from .service import seasonal_feed_service

router = APIRouter(tags=["seasonal-feed"])


@router.get("/seasonal-feed", response_model=SeasonalFeedResponse)
def get_seasonal_feed() -> SeasonalFeedResponse:
    return seasonal_feed_service.get_seasonal_feed()
