"""Utilities for resolving nearby places using the Google Maps Places API and a
small JSON-backed cache used by the GUI.

This module provides:
- get_nearby_places: a thin wrapper around googlemaps.Client.places_nearby that
  follows next_page_token pagination and returns up to `max_results` results.
- GeoUtil: a caching convenience class that stores place search results in a
  JSON file (default: geoutil_cache.json) to avoid repeated network requests.
- PlaceInfo: a small helper to access common fields from a place result and to
  parse plus-code compound_code entries into city/state/country when available.

The GOOGLE_API_KEY environment variable should be set before using the module
so the googlemaps client can authenticate requests.
"""

import os
import time
import logging
import googlemaps
import re
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
logger.info(f"[GEOUTIL] Initializing with API key: {'***' + _API_KEY[-4:] if len(_API_KEY) > 4 else '(empty/not set)'}")

_gmaps = None


def _get_gmaps_client():
    """Lazily initialize the Google Maps client."""
    global _gmaps
    if _gmaps is None:
        key = os.environ.get("GOOGLE_API_KEY", "")
        if not key:
            # Try loading from DB config
            try:
                from lib.web.database import get_db, get_config
                db = get_db()
                try:
                    key = get_config(db, "GOOGLE_API_KEY")
                finally:
                    db.close()
            except Exception:
                pass
        if not key:
            logger.warning("[GEOUTIL] No GOOGLE_API_KEY configured — Places API calls will fail")
            return None
        logger.info(f"[GEOUTIL] Creating Google Maps client with key: ***{key[-4:]}")
        _gmaps = googlemaps.Client(key=key)
    return _gmaps


def _get_nearby_places(lat: float, lng: float, radius: int = 1000, keyword: str = None, place_type: str = None, max_results: int = 60):
    """Return nearby places from the Google Maps Places API.

    This function performs an initial places_nearby request and follows
    pagination using next_page_token when present. A short sleep is applied
    between page requests because the token may not be immediately valid.

    Parameters:
    - lat, lng: latitude and longitude of the search origin (floats).
    - radius: search radius in meters (int). Ignored if rank_by is used in the
      underlying API (not used here).
    - keyword: optional free-text keyword to bias results.
    - place_type: optional place type string (e.g. "restaurant") to filter
      results.
    - max_results: maximum number of place objects to return (default 60).

    Returns:
    - A list of dict objects as returned by the Google Maps Places API. Each
      entry corresponds to a single place result (may include fields like
      'name', 'vicinity', 'rating', 'plus_code', etc.).

    Notes:
    - The function may perform multiple HTTP requests to gather enough
      paginated results; callers should be tolerant of network latency.
    - The caller is responsible for ensuring the googlemaps client is
      configured with a valid API key via the GOOGLE_API_KEY environment
      variable.
    """
    logger.info(f"[GEOUTIL] API request: lat={lat}, lng={lng}, radius={radius}, keyword={keyword}, type={place_type}, max={max_results}")
    location = (lat, lng)
    results = []

    try:
        client = _get_gmaps_client()
        if client is None:
            logger.warning("[GEOUTIL] No Google Maps client available, returning empty results")
            return []

        # initial request
        response: dict = client.places_nearby(location=location,
                                              radius=radius,
                                              keyword=keyword,
                                              open_now=False,
                                              type=place_type)
        results.extend(response.get("results", []))
        logger.info(f"[GEOUTIL] Initial response: {len(response.get('results', []))} results, status={response.get('status', 'unknown')}")

        # follow next_page_token if present (may need a short delay)
        while "next_page_token" in response and len(results) < max_results:
            try:
                time.sleep(2)  # token becomes valid after a short delay
                response = client.places_nearby(page_token=response["next_page_token"])
                results.extend(response.get("results", []))
                logger.info(f"[GEOUTIL] Pagination: total {len(results)} results so far")
            except Exception as page_err:
                logger.warning(f"[GEOUTIL] Pagination error (keeping {len(results)} results already fetched): {page_err}")
                break
    except Exception as e:
        logger.error(f"[GEOUTIL] API error: {type(e).__name__}: {e}")
        return []

    logger.info(f"[GEOUTIL] Returning {len(results[:max_results])} results")
    return results[:max_results]


class PlaceInfo:
    """Helper wrapper around a single Google Maps place result dict.

    Provides convenient properties for commonly used fields like name,
    address, rating, and parsed city/state/country when the place includes a
    plus_code with a compound_code component.

    Construct with the raw place dict returned by the Places API:
      info = PlaceInfo(place_dict)
      print(info.name, info.address, info.rating)
    """

    def __init__(self, place_data: dict):
        self._place_data = place_data
        self.address_info = self._get_address_info()

    @property
    def location(self) -> Tuple[float, float]:
        loc = self._place_data.get("geometry", {}).get("location", {})
        return (float(loc.get("lat", 0.0)), float(loc.get("lng", 0.0)))

    @property
    def name(self) -> str:
        """The place name (empty string if not present)."""
        return self._place_data.get("name", "")

    @property
    def address(self) -> str:
        """A human-readable address (vicinity or formatted_address)."""
        return self._place_data.get("vicinity") or self._place_data.get("formatted_address", "")

    @property
    def rating(self) -> float:
        """Numeric rating for the place or NaN if unavailable."""
        return float(self._place_data.get("rating", float('nan')))

    @property
    def city(self) -> str:
        """Best-effort city name extracted from plus_code or address string."""
        city = self.address_info.get("city", "")
        if not city:
            city = self.address
            if ',' in city:
                city = city.split(',')[1].strip()
        return city

    @property
    def state(self) -> str:
        """State or region code if available from parsed plus_code."""
        return self.address_info.get("state", "")

    @property
    def country(self) -> str:
        """Country name or code if available from parsed plus_code."""
        return self.address_info.get("country", "")

    _comp_code_pattern = re.compile(
        r'([23456789CFGHJMPQRVWX]{4,}[+][23456789CFGHJMPQRVWX]{2,}),*(.+?), ([A-Z]{2}), ([A-Z]+)')

    def _get_address_info(self) -> dict:
        """Parse plus_code compound_code to extract plus_code, city, state, country.

        Returns an empty dict if no compound_code is present or if parsing fails.
        """
        plus_code = self._place_data.get("plus_code", {})
        address_info = {}
        if "compound_code" in plus_code:
            compound_code = plus_code["compound_code"]
            match = self._comp_code_pattern.match(compound_code)
            if match:
                address_info["plus_code"] = match.group(1).strip()
                address_info["city"] = match.group(2).strip()
                address_info["state"] = match.group(3).strip()
                address_info["country"] = match.group(4).strip()
        return address_info

    def __str__(self):
        return f"{self.name} - {self.address} ({self.city}, {self.state}, {self.country}) Rating: {self.rating}"


class GeoUtil:
    """Cache wrapper around the module-level get_nearby_places function.

    GeoUtil stores search results in a simple in-memory dict and persists it to
    a JSON file (self.filename). Keys are stable string encodings of the
    request parameters (rounded lat/lng) so repeated identical queries return
    cached results without performing network requests.

    Typical usage:
      geo = GeoUtil()
      places = geo.get_nearby_places(37.4, -122.1, radius=500)

    Public methods:
    - get_nearby_places(...): returns cached results if available, otherwise
      performs a search and caches the result.
    - clear_cache(): clears the in-memory and on-disk cache.
    - get_cache(): returns the current in-memory cache dict.
    """

    def __init__(self, filename: str = "geoutil_cache.json"):
        self.cache = {}
        self.filename = filename
        self.load_cache(self.filename)

    def set_filename(self, filename: str):
        """Set the JSON filename used for persisting the cache.

        Parameters:
        - filename: path to the JSON file to use.
        """
        self.filename = filename
        self.load_cache(filename)

    def save_cache(self, filename: str):
        """Persist the in-memory cache to the given JSON filename.

        Parameters:
        - filename: path to the JSON file to write.
        """
        import json
        try:
            os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
            with open(filename, "w") as f:
                json.dump(self.cache, f)
        except Exception as e:
            logger.warning(f"[GEOUTIL] Failed to save cache to {filename}: {e}")

    def load_cache(self, filename: str):
        """Load cache contents from a JSON file if it exists.

        Parameters:
        - filename: path to the JSON file to read. If the file does not exist,
          the cache remains empty.
        """
        import json
        if os.path.exists(filename):
            with open(filename, "r") as f:
                self.cache = json.load(f)
            logger.info(f"[GEOUTIL] Loaded cache from {filename}: {len(self.cache)} entries")
        else:
            logger.info(f"[GEOUTIL] No cache file at {filename}, starting empty")

    def get_nearby_places(self, lat: float, lng: float, radius: int = 10000, place_type: str = 'point_of_interest', keyword: str = None, max_results: int = 60) -> List['PlaceInfo']:
        """Get nearby places using the cache when possible.

        Parameters are the same as the module-level get_nearby_places function.

        Behavior:
        - Rounds lat/lng to 6 decimal places to create a stable cache key.
        - If a cached entry exists it is returned immediately.
        - Otherwise performs a network query, stores the result and persists the
          cache to disk.

        Returns:
        - A list of place dicts (same format as get_nearby_places).
        """
        import json
        lat = round(float(lat), 6)
        lng = round(float(lng), 6)
        # create a JSON-serializable cache key (round lat/lng to 6 decimal places for stable keys)
        key_obj = [lat, lng, int(radius), place_type,
                   keyword, int(max_results)]
        cache_key = ';'.join(map(str, key_obj))
        if cache_key in self.cache:
            places = self.cache[cache_key]
            logger.info(f"[GEOUTIL] Cache HIT for key={cache_key[:40]}... ({len(places)} places)")
        else:
            logger.info(f"[GEOUTIL] Cache MISS for key={cache_key[:40]}... calling API")
            # call module-level function with explicit keyword args to avoid parameter-order bugs
            places = _get_nearby_places(
                lat, lng, radius=radius, keyword=keyword, place_type=place_type, max_results=max_results)
            self.cache[cache_key] = places
            self.save_cache(self.filename)
            logger.info(f"[GEOUTIL] Cached {len(places)} places, saved to {self.filename}")

        places_info = [PlaceInfo(place) for place in places]
        # Sort places by distance from the query point
        places_info.sort(key=lambda p: (p.location[0]-lat)**2 + (p.location[1]-lng)**2)
        logger.info(f"[GEOUTIL] Returning {len(places_info)} PlaceInfo objects for ({lat}, {lng})")
        return places_info

    def clear_cache(self):
        """Clear the in-memory cache and persist the empty cache to disk."""
        self.cache = {}
        self.save_cache(self.filename)

    def get_cache(self):
        """Return the in-memory cache dict.

        The returned dict maps cache key strings to lists of place dictionaries.
        """
        return self.cache


_singleton_geo_util: GeoUtil = None


def get_singleton_geo_util(filename: str = "cache/geoutil_cache.json") -> GeoUtil:
    """Return the singleton instance of the geo utility."""
    global _singleton_geo_util
    if _singleton_geo_util is None:
        logger.info(f"[GEOUTIL] Creating singleton GeoUtil with cache file: {filename}")
        _singleton_geo_util = GeoUtil(filename=filename)
    return _singleton_geo_util
