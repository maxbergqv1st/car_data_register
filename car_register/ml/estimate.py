"""Värderar en bil: samma bil predikteras som privat OCH som handlare."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from .. import config
from ..models import FEATURE_COLUMNS

# Värderingsavdrag: träningsdatan är handlarnas UTBUDSpriser som ligger högt.
# Dra alltid av 20% för ett realistiskt värde — gäller både privat och handlare.
VALUATION_DISCOUNT = 0.20


@lru_cache(maxsize=1)
def _load(model_path: str):
    return joblib.load(model_path)


def predict_value(
    cars: pd.DataFrame, model_path: Path | str = config.MODEL_PATH
) -> list[int]:
    """Modellens värdering per rad, med avdraget påslaget. Kräver FEATURE_COLUMNS."""
    model = _load(str(model_path))
    factor = 1 - VALUATION_DISCOUNT
    X = cars.reindex(columns=FEATURE_COLUMNS)
    return [int(round(p * factor)) for p in model.predict(X)]


def estimate(car: dict, model_path: Path | str = config.MODEL_PATH) -> dict:
    """Returnerar {'privat': kr, 'handlare': kr} för en bil (avdrag inräknat).

    `car` ska innehålla alla FEATURE_COLUMNS utom seller_type (den sätts här).
    """
    rows = pd.DataFrame([{**car, "seller_type": s} for s in ("privat", "handlare")])
    return dict(zip(("privat", "handlare"), predict_value(rows, model_path)))
