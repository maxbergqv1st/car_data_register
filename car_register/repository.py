"""Data-access-lager: ENDA vägen mellan applikationen och SQLite.

Säkerhet (grundläggande):
- Alla queries är parametriserade (?), aldrig sträng-interpolation av värden.
- Läsning sker via read-only-koppling.
- Kolumnnamn (som inte kan parametriseras) valideras mot en whitelist.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd

from . import config, db
from .models import CarListing

# Kolumner UI:t får filtrera/gruppera på. Skydd mot injection via kolumnnamn.
_ALLOWED_COLUMNS = {
    "brand", "model", "fuel", "gearbox", "seller_type", "model_year", "location",
}

_INSERT = """
INSERT OR IGNORE INTO listings
    (source, source_url, scraped_at, brand, model, model_year, mileage_km,
     fuel, gearbox, horsepower, seller_type, price_sek, location)
VALUES (:source, :source_url, :scraped_at, :brand, :model, :model_year,
        :mileage_km, :fuel, :gearbox, :horsepower, :seller_type, :price_sek,
        :location)
"""


def insert_listings(
    listings: list[CarListing], db_path: Path | str = config.DB_PATH
) -> int:
    """Sparar validerade annonser. Returnerar antal nya rader (dubletter ignoreras)."""
    db.init_db(db_path)
    rows = []
    for lst in listings:
        d = lst.model_dump()
        d["scraped_at"] = lst.scraped_at.isoformat()
        rows.append(d)
    with db.get_conn(db_path) as conn:
        before = conn.total_changes
        conn.executemany(_INSERT, rows)
        return conn.total_changes - before


def load_dataframe(db_path: Path | str = config.DB_PATH) -> pd.DataFrame:
    """Hela tabellen som DataFrame för ML-träning."""
    with db.get_ro_conn(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM listings", conn)


def fetch_listings(
    brand: Optional[str] = None,
    seller_type: Optional[str] = None,
    limit: int = 200,
    db_path: Path | str = config.DB_PATH,
) -> list[dict]:
    """Annonser för UI-bläddring. Parametriserade filter, read-only."""
    where, params = [], []
    if brand:
        where.append("brand = ?")
        params.append(brand)
    if seller_type:
        where.append("seller_type = ?")
        params.append(seller_type)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    sql = f"SELECT * FROM listings {clause} ORDER BY scraped_at DESC LIMIT ?"
    params.append(int(limit))
    with db.get_ro_conn(db_path) as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def distinct_values(column: str, db_path: Path | str = config.DB_PATH) -> list:
    """Unika värden i en kolumn (för UI-dropdowns). Kolumn måste vara whitelistad."""
    if column not in _ALLOWED_COLUMNS:
        raise ValueError(f"Otillåten kolumn: {column!r}")
    sql = f"SELECT DISTINCT {column} FROM listings WHERE {column} IS NOT NULL ORDER BY 1"
    with db.get_ro_conn(db_path) as conn:
        return [r[0] for r in conn.execute(sql).fetchall()]


def count(db_path: Path | str = config.DB_PATH) -> int:
    try:
        with db.get_ro_conn(db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    except sqlite3.OperationalError:
        return 0  # DB finns inte än
