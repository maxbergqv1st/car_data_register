"""AutoUncle-scraper — mot deras faktiska struktur (verifierad 2026-09).

AutoUncle är en aggregator (drar in Blocket + handlarannonser), så en källa
räcker. Listsidan `/se/begagnade-bilar?page=N` server-renderar 25 bilar per sida
som schema.org JSON-LD (`<script type="application/ld+json">` → @graph → ItemList
→ Vehicle). Allt vi behöver finns där → INGA detaljsido-requests.

robots.txt tillåter listsidorna men blockerar filtrerad sök (`s[...]`-params),
så vi paginerar bara med `?page=`. Rate-limit/robots-koll sköts i base.get.

ponytail: KALIBRERINGSRATTEN är (a) mil→km-faktorn (sajten visar 'mil', ld+json-
värdet är i mil → ×10) och (b) _FUEL/_TRANSMISSION-tabellerna. Ändrar AutoUncle
sin ld+json är det här det syns. parse_list() är en ren funktion, testbar mot
sparad HTML utan nät.
"""
from __future__ import annotations

import json

from bs4 import BeautifulSoup

from .. import config
from ..models import CarListing
from . import base

# AutoUncles etiketter -> vårt värde-set. Justera om de byter benämning.
_FUEL = {
    "Bensin": "bensin",
    "Diesel": "diesel",
    "Elbil": "el",
    "El/Bensin": "hybrid",
    "El/Diesel": "hybrid",
    "Hybrid": "hybrid",
}
_TRANSMISSION = {"Automat": "automat", "Manuell": "manuell"}


def _types(item: dict) -> list:
    """@type kan vara sträng eller lista."""
    t = item.get("@type", [])
    return t if isinstance(t, list) else [t]


def _car(item: dict) -> CarListing | None:
    """Ett Vehicle-objekt ur ld+json -> CarListing (None om obligatoriskt saknas)."""
    try:
        hp = int(item["vehicleEngine"]["enginePower"]["value"])
    except (KeyError, TypeError, ValueError):
        hp = 100  # saknas ibland (t.ex. elbilar) -> modellens default
    try:
        return CarListing(
            source="autouncle",
            source_url=item["@id"].split("#")[0],
            brand=item["brand"]["name"],
            model=item["model"],
            model_year=int(item["vehicleModelDate"]),
            mileage_km=int(item["mileageFromOdometer"]["value"]) * 10,  # mil -> km
            fuel=_FUEL.get(item.get("fuelType", ""), "okänt"),
            gearbox=_TRANSMISSION.get(item.get("vehicleTransmission", ""), "okänt"),
            horsepower=hp,
            # ponytail: ld+json saknar säljartyp; AutoUncle är handlar-tungt.
            # Sätt handlare tills vi har en säkrare signal (kräver detaljsida).
            seller_type="handlare",
            price_sek=int(item["offers"]["price"]),
        )
    except (KeyError, TypeError, ValueError):
        return None  # ogiltig/ofullständig annons -> hoppa över


def parse_list(html: str) -> list[CarListing]:
    """Ren funktion: listsidans HTML -> lista av CarListing."""
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", type="application/ld+json")
    if tag is None or not tag.string:
        return []
    out: list[CarListing] = []
    for node in json.loads(tag.string).get("@graph", []):
        if node.get("@type") != "ItemList":
            continue  # @graph har flera ItemList (breadcrumb + bilar)
        for el in node.get("itemListElement", []):
            item = el.get("item")
            if isinstance(item, dict) and "Vehicle" in _types(item):
                car = _car(item)
                if car:
                    out.append(car)
    return out


def scrape(pages: int = 1, max_items: int | None = None) -> list[CarListing]:
    """Hämtar `pages` listsidor (25 bilar/sida). Rate-limitas i base.get."""
    listings: list[CarListing] = []
    for page in range(1, pages + 1):
        resp = base.get(config.AUTOUNCLE_SEARCH_URL, params={"page": page})
        listings.extend(parse_list(resp.text))
        if max_items and len(listings) >= max_items:
            return listings[:max_items]
    return listings
