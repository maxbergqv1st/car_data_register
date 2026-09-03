"""Fyndanalys: spottbilligt pris = fynd, ockerpris = dyr, ranking sorterad."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from car_register import synthetic  # noqa: E402
from car_register.ml import train, value  # noqa: E402

_CAR = {
    "brand": "Volvo",
    "model": "V60",
    "model_year": 2019,
    "mileage_km": 50_000,
    "horsepower": 150,
    "fuel": "diesel",
    "gearbox": "automat",
    "seller_type": "privat",
}


def _trained_model(tmp_path) -> tuple[pd.DataFrame, Path]:
    df = pd.DataFrame([lst.model_dump() for lst in synthetic.generate(400)])
    model_path = tmp_path / "model.joblib"
    train.train(df, model_path=model_path)
    return df, model_path


def test_deal_verdicts(tmp_path):
    _, mp = _trained_model(tmp_path)

    cheap = value.deal(_CAR, asking_price=1, model_path=mp)
    assert cheap["verdict"] == "fynd" and cheap["diff"] > 0

    dear = value.deal(_CAR, asking_price=10_000_000, model_path=mp)
    assert dear["verdict"] == "dyr" and dear["diff"] < 0


def test_rank_deals_sorted_best_first(tmp_path):
    df, mp = _trained_model(tmp_path)
    ranked = value.rank_deals(df, top=10, model_path=mp)
    pct = ranked["pct_below_market"].tolist()
    assert pct == sorted(pct, reverse=True)  # bästa fynd överst


def test_comparables_counts_peers(tmp_path):
    df, _ = _trained_model(tmp_path)
    stats = value.comparables(df, "Volvo", "V60")
    assert stats["n"] > 0
    assert stats["min"] <= stats["median"] <= stats["max"]
    assert value.comparables(df, "Volvo", "Rymdskepp")["n"] == 0
