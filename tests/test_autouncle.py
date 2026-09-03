"""parse_list: ld+json -> CarListing. Ren funktion, testas mot inbäddad HTML."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from car_register.scraper import autouncle  # noqa: E402


def _html(*vehicles: dict) -> str:
    """Bygger en minimal listsida med ld+json @graph -> ItemList."""
    graph = [
        # breadcrumb-ItemList (ska ignoreras: item är URL-sträng, ej Vehicle)
        {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "item": "https://x/hem"}]},
        {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i, "item": v}
            for i, v in enumerate(vehicles, 1)]},
    ]
    payload = json.dumps({"@context": "https://schema.org", "@graph": graph})
    return f'<html><body><script type="application/ld+json">{payload}</script></body></html>'


_SUPERB = {
    "@type": ["Product", "Vehicle"],
    "@id": "https://www.autouncle.se/se/d/1-skoda-superb#product",
    "brand": {"@type": "Brand", "name": "Skoda"},
    "model": "Superb",
    "vehicleModelDate": "2018",
    "vehicleTransmission": "Automat",
    "fuelType": "Diesel",
    "vehicleEngine": {"enginePower": {"value": 190, "unitText": "HK"}},
    "mileageFromOdometer": {"value": 18300, "unitCode": "SMI"},  # 18300 mil
    "offers": {"price": 169900, "priceCurrency": "SEK"},
}


def test_parse_list_maps_fields_and_mil_to_km():
    cars = autouncle.parse_list(_html(_SUPERB))
    assert len(cars) == 1  # breadcrumb-ItemList ignorerad
    c = cars[0]
    assert c.brand == "Skoda" and c.model == "Superb"
    assert c.model_year == 2018 and c.horsepower == 190
    assert c.fuel == "diesel" and c.gearbox == "automat"
    assert c.mileage_km == 183_000  # 18300 mil * 10
    assert c.price_sek == 169900 and c.seller_type == "handlare"
    assert c.source == "autouncle" and c.source_url.endswith("/1-skoda-superb")


def test_parse_list_skips_broken_and_maps_ev():
    broken = {**_SUPERB, "offers": {"price": 0}}   # pris 0 -> validering faller
    ev = {**_SUPERB, "@id": "https://x/2#product", "fuelType": "Elbil"}
    del ev["vehicleEngine"]                         # elbil utan hk -> default 100
    cars = autouncle.parse_list(_html(broken, ev))
    assert len(cars) == 1
    assert cars[0].fuel == "el" and cars[0].horsepower == 100


def test_parse_list_reads_private_seller():
    ev = {**_SUPERB, "@id": "https://www.autouncle.se/se/d/7-privat-bil#product"}
    html = _html(ev)
    # React-stream-markör för bil 7 = privatannons (regexen tål quotes utan backslash)
    html = html.replace("</body>", '/7/12345","isPaidClick":true,"isPrivateCar":true</body>')
    cars = autouncle.parse_list(html)
    assert len(cars) == 1 and cars[0].seller_type == "privat"


def test_parse_list_empty_when_no_ld_json():
    assert autouncle.parse_list("<html><body>inget</body></html>") == []
