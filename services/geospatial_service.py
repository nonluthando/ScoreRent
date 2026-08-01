from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

import httpx

GEOAPIFY_API_URL = "https://api.geoapify.com/v1"
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY", "").strip()
REQUEST_TIMEOUT_SECONDS = 15.0

TravelMode = Literal["drive", "walk", "bicycle"]
SUPPORTED_TRAVEL_MODES: set[str] = {"drive", "walk", "bicycle"}


class GeospatialServiceError(RuntimeError):
    """Raised when an address or route cannot be resolved."""


@dataclass(frozen=True)
class GeocodedPlace:
    address: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class RouteResult:
    distance_metres: int
    duration_seconds: int


def _require_api_key() -> str:
    if not GEOAPIFY_API_KEY:
        raise GeospatialServiceError(
            "Distance calculation is not configured yet. Add GEOAPIFY_API_KEY."
        )
    return GEOAPIFY_API_KEY


def geocode_address(address: str) -> GeocodedPlace:
    clean_address = address.strip()
    if not clean_address:
        raise GeospatialServiceError("Enter an address or place name.")

    try:
        response = httpx.get(
            f"{GEOAPIFY_API_URL}/geocode/search",
            params={
                "text": clean_address,
                "format": "json",
                "limit": 1,
                "filter": "countrycode:za",
                "apiKey": _require_api_key(),
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.TimeoutException as exc:
        raise GeospatialServiceError(
            "The location service took too long to respond. Try again."
        ) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            message = "The location service API key was rejected."
        elif exc.response.status_code == 429:
            message = "The location service limit has been reached. Try again later."
        else:
            message = "The location service could not process this address."
        raise GeospatialServiceError(message) from exc
    except (httpx.RequestError, ValueError) as exc:
        raise GeospatialServiceError(
            "The location service is temporarily unavailable."
        ) from exc

    results = payload.get("results") or []
    if not results:
        raise GeospatialServiceError(
            "No matching South African location was found. Add a suburb or city and try again."
        )

    result = results[0]
    try:
        return GeocodedPlace(
            address=result.get("formatted") or clean_address,
            latitude=float(result["lat"]),
            longitude=float(result["lon"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise GeospatialServiceError(
            "The location service returned an incomplete address result."
        ) from exc


def calculate_route(
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
    travel_mode: str,
) -> RouteResult:
    clean_mode = travel_mode.strip().lower()
    if clean_mode not in SUPPORTED_TRAVEL_MODES:
        raise GeospatialServiceError("Choose driving, walking, or cycling.")

    waypoints = (
        f"{origin_latitude},{origin_longitude}|"
        f"{destination_latitude},{destination_longitude}"
    )

    try:
        response = httpx.get(
            f"{GEOAPIFY_API_URL}/routing",
            params={
                "waypoints": waypoints,
                "mode": clean_mode,
                "format": "json",
                "apiKey": _require_api_key(),
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.TimeoutException as exc:
        raise GeospatialServiceError(
            "The route calculation took too long. Try again."
        ) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            message = "The location service API key was rejected."
        elif exc.response.status_code == 429:
            message = "The route calculation limit has been reached. Try again later."
        else:
            message = "A route could not be calculated for these locations."
        raise GeospatialServiceError(message) from exc
    except (httpx.RequestError, ValueError) as exc:
        raise GeospatialServiceError(
            "The route service is temporarily unavailable."
        ) from exc

    results = payload.get("results") or []
    if not results:
        raise GeospatialServiceError(
            "No route was found between the listing and destination."
        )

    route = results[0]
    try:
        return RouteResult(
            distance_metres=max(0, int(round(float(route["distance"])))),
            duration_seconds=max(0, int(round(float(route["time"])))),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise GeospatialServiceError(
            "The route service returned an incomplete result."
        ) from exc
