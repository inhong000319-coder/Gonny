"""Runtime settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings container."""

    app_name: str = os.getenv("APP_NAME", "Gonny Backend")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")
    openweather_api_key: str | None = os.getenv("OPENWEATHER_API_KEY")
    tour_api_key: str | None = os.getenv("TOUR_API_KEY")
    tour_api_base_url: str = os.getenv(
        "TOUR_API_BASE_URL",
        "https://apis.data.go.kr/B551011/KorService1",
    )
    odsay_api_key: str | None = os.getenv("ODSAY_API_KEY")
    odsay_api_base_url: str = os.getenv("ODSAY_API_BASE_URL", "https://api.odsay.com/v1/api")


settings = Settings()
