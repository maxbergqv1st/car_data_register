"""Modellen tränar och ger två rimliga, olika priser (privat vs handlare)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from car_register import synthetic  # noqa: E402
from car_register.ml import estimate, train  # noqa: E402


def test_estimate_private_vs_dealer(tmp_path):
    df = pd.DataFrame([lst.model_dump() for lst in synthetic.generate(400)])
    model_path = tmp_path / "model.joblib"
    metrics = train.train(df, model_path=model_path)
    assert metrics["r2"] > 0.5  # syntetisk data är lärbar

    car = {
        "brand": "Volvo",
        "model": "V60",
        "model_year": 2019,
        "mileage_km": 50_000,
        "horsepower": 150,
        "fuel": "diesel",
        "gearbox": "automat",
    }
    result = estimate.estimate(car, model_path=model_path)

    assert result["privat"] > 0 and result["handlare"] > 0
    # Handlare tar påslag i den syntetiska prismodellen -> ska synas.
    assert result["handlare"] > result["privat"]


def test_discount_and_private_margin(tmp_path):
    df = pd.DataFrame([lst.model_dump() for lst in synthetic.generate(400)])
    model_path = tmp_path / "model.joblib"
    train.train(df, model_path=model_path)

    dealer = {"brand": "Volvo", "model": "V60", "model_year": 2019, "mileage_km": 50_000,
              "horsepower": 150, "fuel": "diesel", "gearbox": "automat", "seller_type": "handlare"}
    raw = estimate._load(str(model_path)).predict(pd.DataFrame([dealer]))[0]
    # handlare: bara 20%-avdraget
    assert estimate.predict_value(pd.DataFrame([dealer]), model_path)[0] == round(raw * 0.8)

    priv = {**dealer, "seller_type": "privat"}
    raw_priv = estimate._load(str(model_path)).predict(pd.DataFrame([priv]))[0]
    # privat: 20%-avdrag OCH privatmarginal
    assert estimate.predict_value(pd.DataFrame([priv]), model_path)[0] == round(raw_priv * 0.8 * 0.87)
