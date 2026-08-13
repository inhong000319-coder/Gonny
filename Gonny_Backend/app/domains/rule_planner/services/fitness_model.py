from __future__ import annotations

import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from app.domains.destination_catalog.schemas import PlaceData
from app.domains.rule_planner.schemas import NormalizedRuleRequest

from .fitness_features import build_tags_for_place_and_request

MODEL_PATH = Path(__file__).resolve().parents[4] / "models" / "place_fitness_model.pkl"


class FitnessModelNotAvailableError(RuntimeError):
    pass


class FitnessScorer:
    def __init__(self, model_path: Path = MODEL_PATH):
        self.model_path = model_path
        self._artifact: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        if self._artifact is None:
            if not self.model_path.exists():
                raise FitnessModelNotAvailableError(
                    f"Trained fitness model not found at {self.model_path}. "
                    "Run scripts/train_fitness_model.py first."
                )
            self._artifact = joblib.load(self.model_path)
        return self._artifact

    def predict(self, place: PlaceData, request: NormalizedRuleRequest) -> float:
        artifact = self._load()
        binarizer = artifact["binarizer"]
        model = artifact["model"]

        tags = build_tags_for_place_and_request(place, request)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            features = binarizer.transform([tags])
        return float(model.predict(features)[0])


@lru_cache(maxsize=1)
def get_fitness_scorer() -> FitnessScorer:
    return FitnessScorer()
