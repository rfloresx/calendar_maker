"""Template rendering and image metadata utilities.

This module provides wx-independent template rendering and EXIF metadata
extraction, shared between the desktop GUI and web GUI.
"""

import re
import datetime
from typing import Any, Dict, List, Optional, Tuple

import PIL.Image
import piexif


# ---------------------------------------------------------------------------
# EXIF metadata extraction
# ---------------------------------------------------------------------------


def _rat2float(r) -> float:
    try:
        n, d = r
        return float(n) / float(d) if d else 0.0
    except Exception:
        return float(r) if isinstance(r, (int, float)) else 0.0


def _dms_to_deg(dms) -> float:
    deg = _rat2float(dms[0])
    minutes = _rat2float(dms[1])
    seconds = _rat2float(dms[2]) if len(dms) > 2 else 0.0
    return deg + minutes / 60.0 + seconds / 3600.0


def gps_from_exif(exif_dict) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Extract GPS coordinates from a piexif-parsed EXIF dict."""
    gps = exif_dict.get("GPS", {}) or {}
    norm: Dict[Any, Any] = {}
    for k, v in gps.items():
        ik = int(k) if isinstance(k, str) and k.isdigit() else k
        norm[ik] = v

    def decode_ref(x: Any):
        if isinstance(x, bytes):
            return x.decode(errors="ignore")
        if isinstance(x, (tuple, list)) and len(x) == 1 and isinstance(x[0], bytes):
            return x[0].decode(errors="ignore")
        return x

    lat = lon = alt = None
    lat_ref = decode_ref(norm.get(piexif.GPSIFD.GPSLatitudeRef) or norm.get(1))
    lon_ref = decode_ref(norm.get(piexif.GPSIFD.GPSLongitudeRef) or norm.get(3))
    lat_val = norm.get(piexif.GPSIFD.GPSLatitude) or norm.get(2)
    lon_val = norm.get(piexif.GPSIFD.GPSLongitude) or norm.get(4)
    if lat_val and lat_ref and lon_val and lon_ref:
        lat = _dms_to_deg(lat_val)
        lon = _dms_to_deg(lon_val)
        if str(lat_ref).upper().startswith("S"):
            lat = -abs(lat)
        if str(lon_ref).upper().startswith("W"):
            lon = -abs(lon)
    alt_val = norm.get(piexif.GPSIFD.GPSAltitude) or norm.get(6)
    if alt_val is not None:
        alt = _rat2float(alt_val)
    return lat, lon, alt


def get_image_metadata(image: str) -> Dict[str, Any]:
    """Extract EXIF metadata (DateTimeOriginal, GPS) from an image file.

    Returns a dictionary with discovered keys. Best-effort: returns empty
    dict on failure.
    """
    result: Dict[str, Any] = {}
    try:
        # Fast path: piexif direct parse (JPEG)
        try:
            exif_dict = piexif.load(image)
            exif = exif_dict.get("Exif", {})
            dto = exif.get(piexif.ExifIFD.DateTimeOriginal, None)
            if isinstance(dto, bytes):
                try:
                    dto = dto.decode("utf-8")
                except Exception:
                    dto = str(dto)
            if dto is not None:
                result["DateTimeOriginal"] = dto
            lat, lon, alt = gps_from_exif(exif_dict)
            if lat is not None and lon is not None:
                result["GPSLatitude"] = lat
                result["GPSLongitude"] = lon
            if alt is not None:
                result["GPSAltitude"] = alt
            return result
        except Exception:
            pass

        # Fallback: PIL
        with PIL.Image.open(image) as im:
            exif_bytes = im.info.get("exif")
            if not exif_bytes:
                return result
            exif_dict = piexif.load(exif_bytes)
            exif = exif_dict.get("Exif", {})
            dto = exif.get(piexif.ExifIFD.DateTimeOriginal, None)
            if isinstance(dto, bytes):
                try:
                    dto = dto.decode("utf-8")
                except Exception:
                    dto = str(dto)
            if dto is not None:
                result["DateTimeOriginal"] = dto
            lat, lon, alt = gps_from_exif(exif_dict)
            if lat is not None and lon is not None:
                result["GPSLatitude"] = lat
                result["GPSLongitude"] = lon
            if alt is not None:
                result["GPSAltitude"] = alt
    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# ImageInfo (wx-independent)
# ---------------------------------------------------------------------------


class ImageInfo:
    """Container for image filename and metadata dictionary."""

    def __init__(self, filename: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.filename = filename
        self.metadata = metadata if metadata is not None else {}

    @property
    def datetime_original(self) -> Optional[datetime.datetime]:
        """Return DateTimeOriginal as a datetime or None."""
        dto = self.metadata.get("DateTimeOriginal", None)
        if dto is not None and isinstance(dto, bytes):
            try:
                dto = dto.decode("utf-8")
            except Exception:
                dto = str(dto)
        if dto:
            try:
                return datetime.datetime.strptime(dto, "%Y:%m:%d %H:%M:%S")
            except (ValueError, TypeError):
                return None
        return None

    @property
    def places(self) -> list:
        """Return list of PlaceInfo from GPS. Requires geoutil/googlemaps."""
        try:
            from lib.gui.geoutil import get_singleton_geo_util
            lat = self.metadata.get("GPSLatitude")
            lon = self.metadata.get("GPSLongitude")
            if lat is not None and lon is not None:
                return get_singleton_geo_util().get_nearby_places(lat=lat, lng=lon) or []
        except Exception:
            pass
        return []


# ---------------------------------------------------------------------------
# TextTemplate
# ---------------------------------------------------------------------------


class TextTemplate:
    """Simple template renderer supporting {key} and {key:format} placeholders."""

    def __init__(self, template: str = ""):
        self.template = template

    def render(self, context: Dict[str, Any]) -> str:
        """Render the template using a key/value context.

        Supports format specifiers: {key:fmt}. If the value is a datetime
        and a format is given, strftime is used. Missing keys become empty strings.
        """
        text = self.template or ""
        if not text:
            return text

        pattern = r"\{([A-Za-z0-9_.]+)(?::([^}]+))?\}"

        def replace(m: re.Match) -> str:
            key = m.group(1)
            fmt = m.group(2)
            value = context.get(key, "")
            # Normalize NaN floats
            try:
                if isinstance(value, float) and value != value:
                    value = ""
            except Exception:
                pass
            if fmt and isinstance(value, datetime.datetime):
                try:
                    return value.strftime(fmt)
                except Exception:
                    return ""
            return "" if value is None else str(value)

        return re.sub(pattern, replace, text)


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------


def build_text_context(
    image_info: ImageInfo,
    selected_place_index: int = 0,
    overrides: Optional[Dict[str, str]] = None,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a full context dict for TextTemplate rendering.

    Includes place.* keys, date, img.date, and year.
    """
    ctx: Dict[str, Any] = {
        "place.name": "",
        "place.city": "",
        "place.state": "",
        "place.country": "",
        "place.address": "",
        "place.rating": "",
        "img.date": "",
    }

    # Date
    dt = image_info.datetime_original
    if dt is not None:
        try:
            ctx["img.date"] = dt.strftime("%Y-%m-%d")
        except Exception:
            ctx["img.date"] = ""

    # Place info
    if overrides and isinstance(overrides, dict) and any(
        v is not None and v != "" for v in overrides.values()
    ):
        ctx["place.name"] = str(overrides.get("name", "") or "")
        ctx["place.city"] = str(overrides.get("city", "") or "")
        ctx["place.state"] = str(overrides.get("state", "") or "")
        ctx["place.country"] = str(overrides.get("country", "") or "")
        ctx["place.address"] = str(overrides.get("address", "") or "")
        rating = overrides.get("rating", "")
        try:
            ctx["place.rating"] = (
                "" if (isinstance(rating, float) and rating != rating) else str(rating or "")
            )
        except Exception:
            ctx["place.rating"] = str(rating or "")
    else:
        # From metadata places
        places = image_info.places
        if places:
            try:
                idx = max(0, min(int(selected_place_index), len(places) - 1))
            except Exception:
                idx = 0
            place = places[idx]
            try:
                ctx["place.name"] = str(getattr(place, "name", "") or "")
                ctx["place.city"] = str(getattr(place, "city", "") or "")
                ctx["place.state"] = str(getattr(place, "state", "") or "")
                ctx["place.country"] = str(getattr(place, "country", "") or "")
                ctx["place.address"] = str(getattr(place, "address", "") or "")
                rating = getattr(place, "rating", "")
                ctx["place.rating"] = (
                    "" if (isinstance(rating, float) and rating != rating) else str(rating or "")
                )
            except Exception:
                pass

    # Raw datetime for {date:%...}
    ctx["date"] = dt
    if year is not None:
        ctx["year"] = year

    return ctx
