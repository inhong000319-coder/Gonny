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
        # KorService1 was retired by the Korea Tourism Organization; TourAPI
        # 4.0 serves the same endpoints under KorService2. Verified live
        # against apis.data.go.kr while building coordinate lookup - v1
        # returns NO_OPENAPI_SERVICE_ERROR for every call.
        "https://apis.data.go.kr/B551011/KorService2",
    )
    odsay_api_key: str | None = os.getenv("ODSAY_API_KEY")
    odsay_api_base_url: str = os.getenv("ODSAY_API_BASE_URL", "https://api.odsay.com/v1/api")
    database_url: str = os.getenv("DATABASE_URL", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    rule_note_generation_mode: str = os.getenv("RULE_NOTE_GENERATION_MODE", "template")
    rule_note_model: str = os.getenv("RULE_NOTE_MODEL", "")


settings = Settings()
