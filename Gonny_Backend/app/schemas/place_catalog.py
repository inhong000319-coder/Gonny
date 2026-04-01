from pydantic import BaseModel, ConfigDict, Field


class PlaceData(BaseModel):
    id: str
    name: str
    category: list[str]
    budget_level: list[str]
    suitable_for: list[str]
    time_fit: list[str]
    area: str
    duration_hours: int = Field(ge=1, le=12)
    priority: int = Field(ge=1, le=10)
    pace: list[str]
    mobility: list[str]
    summary: str

    model_config = ConfigDict(str_strip_whitespace=True)


class CityPlaceCatalog(BaseModel):
    continent: str
    country: str
    city: str
    aliases: list[str] = []
    default_days: int = 3
    places: list[PlaceData]

    model_config = ConfigDict(str_strip_whitespace=True)
