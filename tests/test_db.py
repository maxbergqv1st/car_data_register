"""Roundtrip: insert -> query. Plus att read-only-kopplingen inte kan skriva."""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from car_register import db, repository, synthetic  # noqa: E402


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test.db"


def test_insert_and_fetch_roundtrip(tmp_db):
    listings = synthetic.generate(30)
    new = repository.insert_listings(listings, db_path=tmp_db)
    assert new == 30

    # Dubletter ignoreras (samma source_url) -> 0 nya.
    assert repository.insert_listings(listings, db_path=tmp_db) == 0

    rows = repository.fetch_listings(limit=100, db_path=tmp_db)
    assert len(rows) == 30
    assert {"brand", "price_sek", "seller_type"} <= rows[0].keys()


def test_seller_filter_is_parameterized(tmp_db):
    repository.insert_listings(synthetic.generate(50), db_path=tmp_db)
    only_dealer = repository.fetch_listings(seller_type="handlare", db_path=tmp_db)
    assert all(r["seller_type"] == "handlare" for r in only_dealer)


def test_distinct_column_whitelist(tmp_db):
    repository.insert_listings(synthetic.generate(10), db_path=tmp_db)
    with pytest.raises(ValueError):
        repository.distinct_values("price_sek; DROP TABLE listings", db_path=tmp_db)


def test_readonly_connection_cannot_write(tmp_db):
    db.init_db(tmp_db)
    with db.get_ro_conn(tmp_db) as conn:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO listings (source) VALUES ('x')")
