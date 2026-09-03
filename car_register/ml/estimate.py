"""Värderar en bil: samma bil predikteras som privat OCH som handlare."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from .. import config
from ..models import FEATURE_COLUMNS


@lru_cache(maxsize=1)
def _load(model_path: str):
    return joblib.load(model_path)


def estimate(car: dict, model_path: Path | str = config.MODEL_PATH) -> dict:
    """Returnerar {'privat': kr, 'handlare': kr} för en bil.

    `car` ska innehålla alla FEATURE_COLUMNS utom seller_type (den sätts här).
    """
    model = _load(str(model_path))
    out = {}
    for seller in ("privat", "handlare"):
        row = {**car, "seller_type": seller}
        X = pd.DataFrame([{c: row.get(c) for c in FEATURE_COLUMNS}])
        out[seller] = int(round(model.predict(X)[0]))
    return out
