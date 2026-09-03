"""Respektfull HTTP-hämtning: robots.txt, rate-limit, retry med backoff.

Ingen genväg här — vi vill inte hamra en riktig sajt.
"""
from __future__ import annotations

import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from .. import config

_last_request_at = 0.0
_robots_cache: dict[str, RobotFileParser] = {}


def _robots(url: str) -> RobotFileParser:
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots_cache:
        rp = RobotFileParser()
        # Hämta robots.txt med SAMMA User-Agent som sidorna. RobotFileParser.read()
        # använder default-UA, som sajter (t.ex. AutoUncle) svarar 403 på -> parsern
        # skulle då tolka det som "allt förbjudet". Med vår UA får vi rätt regler.
        try:
            resp = requests.get(
                f"{base}/robots.txt",
                headers={"User-Agent": config.USER_AGENT},
                timeout=config.REQUEST_TIMEOUT,
            )
            rp.parse(resp.text.splitlines() if resp.ok else [])
        except requests.RequestException:
            rp.parse([])  # oåtkomlig robots.txt -> tillåt (RFC 9309: 4xx = allow)
        _robots_cache[base] = rp
    return _robots_cache[base]


def allowed(url: str) -> bool:
    """Får vi hämta den här URL:en enligt robots.txt?"""
    return _robots(url).can_fetch(config.USER_AGENT, url)


def get(url: str, params: dict | None = None) -> requests.Response:
    """GET med robots-koll, global rate-limit och backoff. Höjer vid blockering."""
    global _last_request_at

    if not allowed(url):
        raise PermissionError(f"robots.txt tillåter inte hämtning av {url}")

    # Global rate-limit: minst REQUEST_DELAY_SECONDS mellan requests.
    wait = config.REQUEST_DELAY_SECONDS - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)

    headers = {"User-Agent": config.USER_AGENT, "Accept-Language": "sv-SE,sv"}
    last_exc: Exception | None = None
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url, params=params, headers=headers, timeout=config.REQUEST_TIMEOUT
            )
            _last_request_at = time.monotonic()
            if resp.status_code == 429:  # too many requests -> backa
                time.sleep(config.REQUEST_DELAY_SECONDS * (attempt + 2))
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(config.REQUEST_DELAY_SECONDS * (attempt + 1))
    raise RuntimeError(f"Kunde inte hämta {url}: {last_exc}")
