"""Tränar prismodellen och sparar den med joblib.

En modell, med seller_type som feature -> kan prediktera både privat- och
handlarpris (se estimate.py).
"""
from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split
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


def evaluate(df: pd.DataFrame, k: int = 5, random_state: int = 42) -> dict:
    """Jämför nuvarande modell (RandomForest) mot en LinearRegression-baseline.

    Ren utvärdering vid sidan av train() — tränar/sparar ingen produktionsmodell.
    Per modell: MAE/MSE/RMSE på en 80/20 test-split (samma logik som train()) PLUS
    k-fold korsvalidering på HELA datan, så skillnaden mellan "en split" och
    "medel över flera splits" blir synlig.
    """
    missing = set(FEATURE_COLUMNS + [TARGET]) - set(df.columns)
    if missing:
        raise ValueError(f"Data saknar kolumner: {missing}")

    X, y = df[FEATURE_COLUMNS], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state
    )

    # Nuvarande produktionsmodell + en enkel linjär baseline. Samma preprocessor
    # och samma indata (FEATURE_COLUMNS) för rättvis jämförelse.
    factories = {
        "RandomForest (nuvarande)": lambda: RandomForestRegressor(
            n_estimators=200, random_state=random_state
        ),
        "LinearRegression (baseline)": LinearRegression,
    }

    results = {}
    for name, make in factories.items():
        pipe = Pipeline([("prep", build_preprocessor()), ("model", make())])
        pipe.fit(X_train, y_train)
        preds = pipe.predict(X_test)

        # MAE: genomsnittligt absolut fel i kronor, lätt att tolka.
        mae = mean_absolute_error(y_test, preds)
        # MSE: kvadrerat fel, straffar stora avvikelser hårdare än MAE.
        mse = mean_squared_error(y_test, preds)
        # RMSE: roten ur MSE — samma enhet (kronor) men känsligare för extremvärden.
        rmse = mse ** 0.5

        # Korsvalidering (k-fold): tränar/testar på k olika delar av HELA datan och
        # ger medel ± std -> mer tillförlitligt än en enda slumpmässig split.
        # sklearn returnerar negerade fel, så vi vänder tecknet.
        cv_pipe = Pipeline([("prep", build_preprocessor()), ("model", make())])
        cv_mae = -cross_val_score(cv_pipe, X, y, cv=k, scoring="neg_mean_absolute_error")
        cv_rmse = -cross_val_score(cv_pipe, X, y, cv=k, scoring="neg_root_mean_squared_error")

        results[name] = {
            "mae": mae, "mse": mse, "rmse": rmse,
            "cv_mae_mean": cv_mae.mean(), "cv_mae_std": cv_mae.std(),
            "cv_rmse_mean": cv_rmse.mean(), "cv_rmse_std": cv_rmse.std(),
        }
    return results
