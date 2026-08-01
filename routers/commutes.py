from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import get_current_user
from database import get_conn
from services.geospatial_service import (
    GeospatialServiceError,
    SUPPORTED_TRAVEL_MODES,
    calculate_route,
    geocode_address,
)

router = APIRouter(tags=["commutes"])
templates = Jinja2Templates(directory="templates")


def _now():
    return datetime.now(timezone.utc)


@router.get("/destinations")
def destinations_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM saved_destinations
                WHERE user_id = %s
                ORDER BY label ASC, created_at DESC
                """,
                (user["id"],),
            )
            destinations = cur.fetchall()

    return templates.TemplateResponse(
        "destinations.html",
        {
            "request": request,
            "user": user,
            "destinations": destinations,
            "error": request.query_params.get("error"),
            "success": request.query_params.get("success"),
        },
    )


@router.post("/destinations")
def save_destination(
    request: Request,
    label: str = Form(...),
    address: str = Form(...),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    clean_label = label.strip()
    if not clean_label:
        return RedirectResponse(
            "/destinations?error=" + quote("Give this destination a name, such as Work or Campus."),
            status_code=303,
        )

    try:
        place = geocode_address(address)
    except GeospatialServiceError as exc:
        return RedirectResponse(
            "/destinations?error=" + quote(str(exc)), status_code=303
        )

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO saved_destinations (
                    user_id, label, address, latitude, longitude, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user["id"], clean_label, place.address,
                    place.latitude, place.longitude, _now(), _now(),
                ),
            )
        conn.commit()

    return RedirectResponse(
        "/destinations?success=" + quote(f"{clean_label} was saved."),
        status_code=303,
    )


@router.post("/destinations/{destination_id}/delete")
def delete_destination(request: Request, destination_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM saved_destinations WHERE id = %s AND user_id = %s",
                (destination_id, user["id"]),
            )
        conn.commit()

    return RedirectResponse("/destinations", status_code=303)


@router.post("/listings/{listing_id}/commutes")
def calculate_listing_commute(
    request: Request,
    listing_id: int,
    destination_id: int = Form(...),
    travel_mode: str = Form("drive"),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    clean_mode = travel_mode.strip().lower()
    if clean_mode not in SUPPORTED_TRAVEL_MODES:
        return RedirectResponse(
            f"/listings/{listing_id}?commute_error=" + quote("Choose a valid travel mode."),
            status_code=303,
        )

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM listings WHERE id = %s AND user_id = %s",
                (listing_id, user["id"]),
            )
            listing = cur.fetchone()

            cur.execute(
                "SELECT * FROM saved_destinations WHERE id = %s AND user_id = %s",
                (destination_id, user["id"]),
            )
            destination = cur.fetchone()

        if not listing or not destination:
            return RedirectResponse("/listings", status_code=303)

        try:
            listing_latitude = listing.get("latitude")
            listing_longitude = listing.get("longitude")

            if listing_latitude is None or listing_longitude is None:
                if not listing.get("location"):
                    raise GeospatialServiceError(
                        "Add a listing location before calculating a commute."
                    )
                listing_place = geocode_address(listing["location"])
                listing_latitude = listing_place.latitude
                listing_longitude = listing_place.longitude

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE listings
                        SET latitude = %s, longitude = %s,
                            geocoded_address = %s, updated_at = %s
                        WHERE id = %s AND user_id = %s
                        """,
                        (
                            listing_latitude, listing_longitude,
                            listing_place.address, _now(), listing_id, user["id"],
                        ),
                    )

            route = calculate_route(
                float(listing_latitude),
                float(listing_longitude),
                float(destination["latitude"]),
                float(destination["longitude"]),
                clean_mode,
            )

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO listing_commutes (
                        user_id, listing_id, destination_id, travel_mode,
                        distance_metres, duration_seconds, calculated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (listing_id, destination_id, travel_mode)
                    DO UPDATE SET
                        distance_metres = EXCLUDED.distance_metres,
                        duration_seconds = EXCLUDED.duration_seconds,
                        calculated_at = EXCLUDED.calculated_at
                    """,
                    (
                        user["id"], listing_id, destination_id, clean_mode,
                        route.distance_metres, route.duration_seconds, _now(),
                    ),
                )
            conn.commit()
        except GeospatialServiceError as exc:
            conn.rollback()
            return RedirectResponse(
                f"/listings/{listing_id}?commute_error=" + quote(str(exc)),
                status_code=303,
            )

    return RedirectResponse(
        f"/listings/{listing_id}?commute_success=" + quote("Travel time calculated."),
        status_code=303,
    )
