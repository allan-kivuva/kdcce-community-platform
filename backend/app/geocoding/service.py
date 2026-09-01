"""A pluggable geocoding abstraction — one function (`geocode_address`)
every caller goes through, so swapping the underlying provider later
never touches a route or model. The only provider implemented here is
"offline": a deterministic, non-real placeholder (no network call, no
API key) since this deployment has no paid geocoding vendor configured
and Phase 8 explicitly said not to hardwire one. It derives a stable
pseudo-coordinate from a hash of the address text, constrained to a
real-world bounding box around Nairobi/Kibera (where KDCCE operates) —
useful for exercising the map/matching/distance features end-to-end,
but NOT a real address lookup. A real provider (e.g. an HTTP call to
Nominatim/Google/Mapbox) would replace only `_geocode_offline` below,
behind the same `geocode_address(text)` signature, gated by
GEOCODING_PROVIDER."""

import hashlib

from flask import current_app

# Roughly Nairobi/Kibera's bounding box.
_LAT_RANGE = (-1.335, -1.275)
_LNG_RANGE = (36.75, 36.82)


class GeocodeResult:
    def __init__(self, latitude, longitude, source, accuracy):
        self.latitude = latitude
        self.longitude = longitude
        self.source = source
        self.accuracy = accuracy


def _geocode_offline(address_text):
    digest = hashlib.sha256(address_text.strip().lower().encode("utf-8")).digest()
    lat_fraction = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF
    lng_fraction = int.from_bytes(digest[4:8], "big") / 0xFFFFFFFF
    latitude = _LAT_RANGE[0] + lat_fraction * (_LAT_RANGE[1] - _LAT_RANGE[0])
    longitude = _LNG_RANGE[0] + lng_fraction * (_LNG_RANGE[1] - _LNG_RANGE[0])
    return GeocodeResult(latitude=round(latitude, 6), longitude=round(longitude, 6), source="offline", accuracy="approximate")


def geocode_address(address_text):
    """Returns a GeocodeResult, or None if the address is empty/unusable.
    Never raises for a bad address — a route calling this treats None as
    "could not geocode" and reports that back, not a 500."""
    if not address_text or not address_text.strip():
        return None
    provider = current_app.config.get("GEOCODING_PROVIDER", "offline")
    if provider == "offline":
        return _geocode_offline(address_text)
    # No other provider is wired up in this deployment — see the module
    # docstring. Fail closed (None) rather than silently falling back to
    # the offline stub for a provider name that was actually configured.
    return None
