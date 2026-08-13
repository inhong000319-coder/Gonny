from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.preprocessing import MultiLabelBinarizer

from app.domains.destination_catalog.schemas import PlaceData
from app.domains.destination_catalog.services.repository import DestinationCatalogRepository
from app.domains.rule_planner.services.fitness_features import build_feature_tags

LOCAL_DATA_DIR = PROJECT_ROOT / "local_only" / "data"
FITNESS_SCORE_CSV = LOCAL_DATA_DIR / "fitness_score_ALL.csv"
PERSONA_ATTRIBUTES_CSV = LOCAL_DATA_DIR / "persona_attributes.csv"
MODEL_OUTPUT_PATH = PROJECT_ROOT / "models" / "place_fitness_model.pkl"

RANDOM_STATE = 42
TEST_SIZE = 0.2
OVERFIT_R2_GAP_THRESHOLD = 0.2


def load_persona_attributes() -> dict[str, dict[str, object]]:
    personas: dict[str, dict[str, object]] = {}
    with PERSONA_ATTRIBUTES_CSV.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            personas[row["persona_id"]] = {
                "concepts": [value.strip() for value in row["concepts"].split(",") if value.strip()],
                "style": row["style"].strip(),
                "companion_type": row["companion_type"].strip(),
                "budget_band": row["budget_band"].strip(),
            }
    return personas


def load_places() -> dict[str, PlaceData]:
    repository = DestinationCatalogRepository()
    places: dict[str, PlaceData] = {}
    for catalog in repository.load_catalogs():
        for place in catalog.places:
            places[place.id] = place
    return places


def load_training_rows() -> tuple[list[list[str]], list[float]]:
    personas = load_persona_attributes()
    places = load_places()

    tag_lists: list[list[str]] = []
    scores: list[float] = []
    skipped = 0
    with FITNESS_SCORE_CSV.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            persona = personas.get(row["persona_id"])
            place = places.get(row["place_id"])
            if persona is None or place is None:
                skipped += 1
                continue
            tags = build_feature_tags(
                concepts=persona["concepts"],
                style=persona["style"],
                companion_type=persona["companion_type"],
                budget_band=persona["budget_band"],
                activity_type=place.activity_type,
                mood=place.mood,
                mood_evening_override=place.mood_evening_override,
                visual_feature=place.visual_feature,
                budget_level=place.budget_level,
                suitable_for=place.suitable_for,
                mobility=place.mobility,
            )
            tag_lists.append(tags)
            scores.append(float(row["fitness_score"]))

    if skipped:
        print(f"Skipped {skipped} row(s) with unmatched persona_id/place_id")
    return tag_lists, scores


def build_model() -> GradientBoostingRegressor:
    return GradientBoostingRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        min_samples_leaf=5,
        random_state=RANDOM_STATE,
    )


def train() -> None:
    tag_lists, scores = load_training_rows()
    print(f"Loaded {len(tag_lists)} training rows")

    binarizer = MultiLabelBinarizer()
    features = binarizer.fit_transform(tag_lists)
    target = np.array(scores)
    print(f"Feature vocabulary size: {len(binarizer.classes_)}")

    features_train, features_test, target_train, target_test = train_test_split(
        features, target, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    model = build_model()
    model.fit(features_train, target_train)

    train_pred = model.predict(features_train)
    test_pred = model.predict(features_test)
    train_r2 = r2_score(target_train, train_pred)
    test_r2 = r2_score(target_test, test_pred)
    train_mae = mean_absolute_error(target_train, train_pred)
    test_mae = mean_absolute_error(target_test, test_pred)
    # CSV rows are grouped contiguously by persona_id, so an unshuffled KFold
    # would concentrate whole personas into single folds and understate
    # generalization; shuffle so folds mix persona/place combinations.
    cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_scores = cross_val_score(build_model(), features, target, cv=cv, scoring="r2")

    print("=== Fitness model evaluation ===")
    print(f"Train R^2: {train_r2:.4f}   Train MAE: {train_mae:.2f}")
    print(f"Test  R^2: {test_r2:.4f}   Test  MAE: {test_mae:.2f}")
    print(f"5-fold CV R^2: mean={cv_scores.mean():.4f} std={cv_scores.std():.4f} scores={np.round(cv_scores, 4).tolist()}")
    train_test_gap = train_r2 - test_r2
    train_cv_gap = train_r2 - cv_scores.mean()
    if train_test_gap > OVERFIT_R2_GAP_THRESHOLD or train_cv_gap > OVERFIT_R2_GAP_THRESHOLD:
        print(
            f"WARNING: train R^2 is {train_test_gap:.4f} above the held-out test split and "
            f"{train_cv_gap:.4f} above the 5-fold CV mean (threshold {OVERFIT_R2_GAP_THRESHOLD}); "
            "model may be overfitting."
        )
    else:
        print("Train/test and train/CV R^2 gaps are within tolerance; no strong overfitting signal.")

    MODEL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "binarizer": binarizer,
            "model": model,
            "metrics": {
                "train_r2": float(train_r2),
                "test_r2": float(test_r2),
                "train_mae": float(train_mae),
                "test_mae": float(test_mae),
                "cv_r2_mean": float(cv_scores.mean()),
                "cv_r2_std": float(cv_scores.std()),
                "n_samples": len(scores),
                "n_features": len(binarizer.classes_),
            },
        },
        MODEL_OUTPUT_PATH,
    )
    print(f"Saved model to {MODEL_OUTPUT_PATH}")


if __name__ == "__main__":
    train()
