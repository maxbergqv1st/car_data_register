"""Fyndanalys — svarar på "är den här bilen värd att köpa jämfört med andra?".

Tre vinklar en fyndjägare vill ha:
- deal():        begärt pris mot modellens marknadsvärde -> fynd / marknadspris / dyr.
- comparables(): vad kostar liknande bilar (samma märke+modell) i datan?
- rank_deals():  de mest underprissatta annonserna i DB:n, bästa fynd först.

Marknadsvärde = modellens prediktion givet bilens specar (se ml/estimate.py).
Ligger begärt pris under det -> statistiskt underprissatt = fynd.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .. import config
from ..models import FEATURE_COLUMNS
from .estimate import predict_value

# Gräns för fynd/dyr: >=10% under marknad = fynd, >=10% över = dyr, annars marknadspris.
# ponytail: fast tröskel, gör den till parameter om UI:t behöver justera.
_THRESHOLD = 0.10


def _verdict(pct_below_market: float) -> str:
    if pct_below_market >= _THRESHOLD:
        return "fynd"
    if pct_below_market <= -_THRESHOLD:
        return "dyr"
    return "marknadspris"


def deal(
    car: dict, asking_price: int, model_path: Path | str = config.MODEL_PATH
) -> dict:
    """Är annonspriset ett fynd? `car` måste ha alla FEATURE_COLUMNS inkl seller_type."""
    row = pd.DataFrame([{c: car.get(c) for c in FEATURE_COLUMNS}])
    predicted = predict_value(row, model_path)[0]
    diff = predicted - asking_price  # + = billigare än marknad
    pct = diff / predicted if predicted else 0.0
    return {
        "predicted": predicted,
        "asking": asking_price,
        "diff": diff,
        "pct_below_market": round(pct, 3),
        "verdict": _verdict(pct),
    }


def comparables(df: pd.DataFrame, brand: str, model: str) -> dict:
    """Prisstatistik för samma märke+modell i datan. Inga träffar -> nollor."""
    same = df[(df["brand"] == brand) & (df["model"] == model)]["price_sek"]
    if same.empty:
        return {"n": 0, "median": 0, "min": 0, "max": 0}
    return {
        "n": int(same.size),
        "median": int(same.median()),
        "min": int(same.min()),
        "max": int(same.max()),
    }


# ponytail: rank_deals prediktera in-sample (raderna kan ligga i träningsdatan),
# så residualerna blir optimistiskt små. Duger för att visa relativa fynd i ett
# skolprojekt; för skarpt bruk, prediktera med hold-out/out-of-fold-modell.
def rank_deals(
    df: pd.DataFrame, top: int = 20, model_path: Path | str = config.MODEL_PATH
) -> pd.DataFrame:
    """Annonser rankade efter hur långt under marknadspris de ligger, bäst först."""
    out = df.copy()
    out["market_price"] = predict_value(out, model_path)
    out["diff"] = out["market_price"] - out["price_sek"]
    out["pct_below_market"] = (out["diff"] / out["market_price"]).round(3)
    cols = [
        "brand", "model", "model_year", "mileage_km", "seller_type",
        "price_sek", "market_price", "pct_below_market",
    ]
    return out.sort_values("pct_below_market", ascending=False)[cols].head(top)
