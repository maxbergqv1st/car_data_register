"""Validerad datamodell för en bilannons. Pydantic = trust boundary.

All data (scrapad ELLER från användarformulär) går genom CarListing innan den
når DB eller modellen. Ogiltig data kastas här, inte längre ner i stacken.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

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
    source_url: Optional[str] = None
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    brand: str
    model: str
    model_year: int
    mileage_km: int
    fuel: str
    gearbox: str
    horsepower: int = 100
    seller_type: SellerType
    price_sek: int
    location: Optional[str] = None

    @field_validator("model_year")
    @classmethod
    def _year_rimligt(cls, v: int) -> int:
        if not (1950 <= v <= CURRENT_YEAR + 1):
            raise ValueError(f"model_year {v} utanför rimligt intervall")
        return v

    @field_validator("mileage_km")
    @classmethod
    def _mileage_ickenegativ(cls, v: int) -> int:
        if v < 0:
            raise ValueError("mileage_km kan inte vara negativ")
        return v

    @field_validator("price_sek")
    @classmethod
    def _pris_positivt(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("price_sek måste vara > 0")
        return v

    @field_validator("horsepower")
    @classmethod
    def _hk_positiv(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("horsepower måste vara > 0")
        return v
