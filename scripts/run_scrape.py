"""CLI: scrapa Blocket (eller generera syntetisk data) -> SQLite.

    python scripts/run_scrape.py --query "volvo" --pages 2
    python scripts/run_scrape.py --synthetic 400
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from car_register import repository, synthetic  # noqa: E402
from car_register.scraper import blocket  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Samla in bildata till SQLite.")
    ap.add_argument("--query", default="", help="Blocket-sökord")
    ap.add_argument("--pages", type=int, default=1, help="Antal sök-sidor")
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
            listings = blocket.scrape(args.query, args.pages)
        except (PermissionError, RuntimeError) as exc:
            print(f"Scrape misslyckades: {exc}", file=sys.stderr)
            print("Tips: kör med --synthetic 400 för att utveckla mot fejkad data.")
            sys.exit(1)

    new = repository.insert_listings(listings)
    print(f"Hittade {len(listings)} annonser, {new} nya sparade i DB.")


if __name__ == "__main__":
    main()
