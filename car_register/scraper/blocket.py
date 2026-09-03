"""Blocket-scraper — mot Blockets faktiska struktur (verifierad 2026-09).

Två steg:
1. Sök-sidan har ett <script id="seoStructuredData"> (schema.org JSON-LD) med
   en lista av annonser -> vi plockar ut varje annons-URL.
2. Varje annons-sida har ett inbäddat "data layer" med key/value-par
   (`{"key":"year","value":["2015"]}` osv) med alla specs vi behöver.

ponytail: KALIBRERINGSRATTEN är (a) fält-nycklarna i parse_detail och (b)
kod-tabellerna _FUEL/_TRANSMISSION nedan. Ändrar Blocket sitt data layer är det
här det syns. parse_list_urls() och parse_detail() är rena funktioner och kan
enhetstestas mot sparad HTML utan nät.

Enhet: Blockets `mileage` anges i svenska MIL -> vi lagrar km (× 10).
"""
from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from .. import config
from ..models import CarListing
from . import base

# Blockets numeriska koder -> läsbara värden. Justera om Blocket ändrar kodning.
_FUEL = {"1": "bensin", "2": "diesel", "3": "el", "4": "miljöbränsle/hybrid"}
_TRANSMISSION = {"1": "manuell", "2": "automat"}

_PAIR_RE = re.compile(r'\{"key":"([^"]+)","value":\[([^\]]*)\]\}')


def parse_list_urls(html: str) -> list[str]:
    """Ren funktion: sök-sidans HTML -> lista av annons-URL:er."""
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", id="seoStructuredData")
    if tag is None or not tag.string:
        return []
    data = json.loads(tag.string)
    items = data.get("mainEntity", {}).get("itemListElement", [])
    urls = []
    for el in items:
        url = el.get("item", {}).get("url")
        if url:
            urls.append(url)
    return urls


def _first(value_str: str) -> str | None:
    """Första värdet ur en data-layer-value (`"2015"` eller `"a","b"`)."""
    part = value_str.split(",")[0].strip().strip('"').strip()
    return part or None


def _data_layer(html: str) -> dict[str, str]:
    """Plockar ut key/value-paren från annons-sidans data layer."""
    out: dict[str, str] = {}
    for key, val in _PAIR_RE.findall(html):
        if key not in out:  # första förekomsten vinner
            first = _first(val)
            if first is not None:
                out[key] = first
    return out


def parse_detail(html: str, url: Optional[str] = None) -> CarListing | None:
    """Ren funktion: annons-sidans HTML -> CarListing (None om obligatoriskt saknas)."""
    d = _data_layer(html)
    try:
        brand = d.get("make_text")
        model = d.get("model_text")
        year = d.get("year")
        mileage_mil = d.get("mileage")
        price = d.get("price")
        if not (brand and model and year and mileage_mil and price):
            return None
        return CarListing(
            source="blocket",
            source_url=url or d.get("id"),
            brand=brand,
            model=model,
            model_year=int(year),
            mileage_km=int(mileage_mil) * 10,  # mil -> km
            fuel=_FUEL.get(d.get("fuel", ""), "okänt"),
            gearbox=_TRANSMISSION.get(d.get("transmission", ""), "okänt"),
            seller_type="handlare" if d.get("owner_type") == "professional" else "privat",
            price_sek=int(price),
            location=d.get("zipcode"),
        )
    except Exception:
        return None  # ogiltig annons -> hoppa över, krascha inte hela scrapen


def scrape(
    query: str = "", pages: int = 1, max_items: int | None = None
) -> list[CarListing]:
    """Hämtar `pages` sök-sidor och sen varje annons-sida. Rate-limitas i base.get."""
    urls: list[str] = []
    for page in range(1, pages + 1):
        resp = base.get(config.BLOCKET_SEARCH_URL, params={"q": query, "page": page})
        urls.extend(parse_list_urls(resp.text))
        if max_items and len(urls) >= max_items:
            urls = urls[:max_items]
            break

    listings: list[CarListing] = []
    for url in urls:
        try:
            detail = base.get(url)
        except (PermissionError, RuntimeError):
            continue  # enskild annons kan strula -> fortsätt med resten
        listing = parse_detail(detail.text, url)
        if listing:
            listings.append(listing)
    return listings
