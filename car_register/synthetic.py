"""Genererar realistisk fejkad bildata i samma schema som scrapen.

Används av tester och som `run_scrape.py --synthetic` när Blocket blockerar,
så att DB->ML->UI kan utvecklas oberoende av nätet.
"""
from __future__ import annotations

import random

from .models import CarListing

_BRANDS = {
    "Volvo": ["V60", "V70", "XC60", "S60"],
    "Volkswagen": ["Golf", "Passat", "Tiguan"],
    "Toyota": ["Corolla", "RAV4", "Yaris"],
    "BMW": ["320", "X3", "520"],
    "Audi": ["A4", "A6", "Q5"],
}
_FUELS = ["bensin", "diesel", "el", "hybrid"]
_GEARBOX = ["manuell", "automat"]


def _price(year: int, mileage: int, hp: int, seller: str) -> int:
    """Enkel men rimlig prismodell: nyare/lägre mil/mer hk = dyrare.

    Handlare tar ~15% påslag jämfört med privat (garanti, marginal).
    """
    base = 40_000
    base += (year - 2005) * 9_000
    base -= mileage * 0.12
    base += hp * 120
    base *= 1.15 if seller == "handlare" else 1.0
    noise = random.uniform(0.9, 1.1)
    return max(15_000, int(base * noise))


def generate(n: int = 400, seed: int = 42) -> list[CarListing]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        brand = rng.choice(list(_BRANDS))
        model = rng.choice(_BRANDS[brand])
        year = rng.randint(2005, 2023)
        mileage = rng.randint(1_000, 250_000)
        hp = rng.choice([90, 110, 140, 150, 190, 245])
        seller = rng.choice(["privat", "handlare"])
        out.append(
            CarListing(
                source="synthetic",
                source_url=f"synthetic://{i}",
                brand=brand,
                model=model,
                model_year=year,
                mileage_km=mileage,
                fuel=rng.choice(_FUELS),
                gearbox=rng.choice(_GEARBOX),
                horsepower=hp,
                seller_type=seller,
                price_sek=_price(year, mileage, hp, seller),
                location=rng.choice(["Stockholm", "Göteborg", "Malmö", "Uppsala"]),
            )
        )
    return out
