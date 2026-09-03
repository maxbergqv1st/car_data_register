"""Validerad datamodell för en bilannons. Pydantic = trust boundary.

All data (scrapad ELLER från användarformulär) går genom CarListing innan den
når DB eller modellen. Ogiltig data kastas här, inte längre ner i stacken.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

CURRENT_YEAR = datetime.now(timezone.utc).year

SellerType = Literal["privat", "handlare"]

# Kolumnerna modellen tränar på (måste matcha ml/features.py).
CATEGORICAL_FEATURES = ["brand", "model", "fuel", "gearbox", "seller_type"]
NUMERIC_FEATURES = ["model_year", "mileage_km", "horsepower"]
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET = "price_sek"


class CarListing(BaseModel):
    """En bilannons. Fält utan default är obligatoriska."""

    source: str
    source_url: str | None = None
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    brand: str
    model: str
    model_year: int = Field(ge=1950, le=CURRENT_YEAR + 1)
    mileage_km: int = Field(ge=0)
    fuel: str
    gearbox: str
    horsepower: int = Field(default=100, gt=0)
    seller_type: SellerType
    price_sek: int = Field(gt=0)
    location: str | None = None
