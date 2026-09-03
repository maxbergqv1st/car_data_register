"""Tränar prismodellen och sparar den med joblib.

En modell, med seller_type som feature -> kan prediktera både privat- och
handlarpris (se estimate.py).
"""
from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from .. import config
from ..models import FEATURE_COLUMNS, TARGET
from .features import build_preprocessor


def train(df: pd.DataFrame, model_path: Path | str = config.MODEL_PATH) -> dict:
    """Tränar på df och sparar pipelinen. Returnerar utvärderingsmått."""
    missing = set(FEATURE_COLUMNS + [TARGET]) - set(df.columns)
    if missing:
        raise ValueError(f"Data saknar kolumner: {missing}")

    X, y = df[FEATURE_COLUMNS], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    pipe = Pipeline(
        [
            ("prep", build_preprocessor()),
            ("model", RandomForestRegressor(n_estimators=200, random_state=42)),
        ]
    )
    pipe.fit(X_train, y_train)

    preds = pipe.predict(X_test)
    metrics = {
        "mae": float(mean_absolute_error(y_test, preds)),
        "r2": float(r2_score(y_test, preds)),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }

    joblib.dump(pipe, model_path)
    return metrics
