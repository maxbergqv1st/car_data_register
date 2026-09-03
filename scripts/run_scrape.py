"""CLI: scrapa AutoUncle (eller generera syntetisk data) -> SQLite.

    python scripts/run_scrape.py --pages 40      # ~1000 bilar (25/sida)
    python scripts/run_scrape.py --synthetic 400
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from car_register import repository, synthetic  # noqa: E402
from car_register.scraper import autouncle  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Samla in bildata till SQLite.")
    ap.add_argument("--pages", type=int, default=1, help="Antal listsidor (25 bilar/sida)")
    ap.add_argument(
        "--synthetic",
        type=int,
        metavar="N",
        help="Hoppa över scraping, generera N syntetiska annonser istället",
    )
    args = ap.parse_args()

    if args.synthetic:
        listings = synthetic.generate(args.synthetic)
    else:
        try:
            listings = autouncle.scrape(args.pages)
        except (PermissionError, RuntimeError) as exc:
            print(f"Scrape misslyckades: {exc}", file=sys.stderr)
            print("Tips: kör med --synthetic 400 för att utveckla mot fejkad data.")
            sys.exit(1)

    new = repository.insert_listings(listings)
    print(f"Hittade {len(listings)} annonser, {new} nya sparade i DB.")


if __name__ == "__main__":
    main()
