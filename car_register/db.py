"""SQLite-schema och kopplingar.

Två sätt att öppna DB:n:
- get_conn(): läs/skriv, för scrape och init.
- get_ro_conn(): READ-ONLY (URI mode=ro), för frontend/läsning. Kan fysiskt
  inte skriva — även om en bugg i UI:t försöker.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT NOT NULL,
    source_url   TEXT,
    scraped_at   TEXT NOT NULL,
    brand        TEXT NOT NULL,
    model        TEXT NOT NULL,
    model_year   INTEGER NOT NULL,
    mileage_km   INTEGER NOT NULL,
    fuel         TEXT NOT NULL,
    gearbox      TEXT NOT NULL,
    horsepower   INTEGER NOT NULL,
    seller_type  TEXT NOT NULL CHECK (seller_type IN ('privat', 'handlare')),
    price_sek    INTEGER NOT NULL CHECK (price_sek > 0),
    location     TEXT,
    UNIQUE (source, source_url)
);
"""


def get_conn(db_path: Path | str = config.DB_PATH) -> sqlite3.Connection:
    """Läs/skriv-koppling. Skapar data-katalogen vid behov."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_ro_conn(db_path: Path | str = config.DB_PATH) -> sqlite3.Connection:
    """Read-only-koppling för frontend. Skrivförsök ger OperationalError."""
    uri = f"file:{Path(db_path)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str = config.DB_PATH) -> None:
    """Skapar tabellen om den inte finns."""
    with get_conn(db_path) as conn:
        conn.executescript(SCHEMA)
