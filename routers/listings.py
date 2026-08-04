from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import get_current_user
from database import get_conn
from services.geospatial_service import (
    GeospatialServiceError,
    calculate_route,
    geocode_address,
)

router = APIRouter(tags=["saved listings"])
templates = Jinja2Templates(directory="templates")
TRAVEL_MODES = ("drive", "walk", "bicycle")
TRAVEL_MODE_LABELS = {
    "drive": "Driving",
    "walk": "Walking",
    "bicycle": "Cycling",
}


def _clean_list(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def _load_json(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def _listing_from_row(row) -> dict:
    listing = dict(row)
    listing["required_documents"] = _load_json(
        listing.pop("required_documents_json"), []
    )
    listing["amenities"] = _load_json(listing.pop("amenities_json"), [])
    listing["pros"] = _load_json(listing.pop("pros_json"), [])
    listing["cons"] = _load_json(listing.pop("cons_json"), [])
    listing["location_is_exact"] = bool(listing.get("location_is_exact"))
    return listing


def _fetch_user_listings(user_id: int) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM listings
                WHERE user_id = %s
                ORDER BY updated_at DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
    return [_listing_from_row(row) for row in rows]


def _selected_listings(all_listings: list[dict], listing_ids: list[int]) -> list[dict]:
    unique_ids = list(dict.fromkeys(listing_ids))
    by_id = {listing["id"]: listing for listing in all_listings}
    return [by_id[listing_id] for listing_id in unique_ids if listing_id in by_id]


def _duration_label(duration_seconds: int) -> str:
    total_minutes = max(1, round(duration_seconds / 60))
    if total_minutes < 60:
        return f"{total_minutes} min"
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours} hr {minutes} min" if minutes else f"{hours} hr"


@router.post("/listings")
def save_listing(
    request: Request,
    listing_name: str = Form(""),
    location: str = Form(""),
    location_is_exact: str = Form("no"),
    rent: int = Form(...),
    deposit: int = Form(...),
    application_fee: int = Form(...),
    area_demand: str = Form("MEDIUM"),
    required_documents: list[str] = Form([]),
    amenities_text: str = Form(""),
    pros_text: str = Form(""),
    cons_text: str = Form(""),
    source_url: str = Form(""),
    notes: str = Form(""),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    clean_location = location.strip()
    exact_location = location_is_exact == "yes" and bool(clean_location)
    title = listing_name.strip() or (
        f"Listing in {clean_location}" if clean_location else f"Listing (R{rent})"
    )
    upfront_cost = int(rent) + int(deposit) + int(application_fee)
    now = datetime.utcnow().isoformat()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO listings (
                    user_id, title, location, location_is_exact,
                    monthly_rent, deposit, application_fee, upfront_cost,
                    area_demand, required_documents_json, amenities_json,
                    pros_json, cons_json, source_url, notes, created_at, updated_at
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    user["id"],
                    title,
                    clean_location,
                    exact_location,
                    int(rent),
                    int(deposit),
                    int(application_fee),
                    upfront_cost,
                    area_demand,
                    json.dumps(_clean_list(required_documents)),
                    json.dumps(_clean_list(amenities_text.splitlines())),
                    json.dumps(_clean_list(pros_text.splitlines())),
                    json.dumps(_clean_list(cons_text.splitlines())),
                    source_url.strip(),
                    notes.strip(),
                    now,
                    now,
                ),
            )
            listing_id = cur.fetchone()["id"]
        conn.commit()

    return RedirectResponse(f"/listings/{listing_id}", status_code=303)


@router.get("/listings")
def saved_listings_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    listings = _fetch_user_listings(int(user["id"]))
    return templates.TemplateResponse(
        "listings.html",
        {"request": request, "user": user, "listings": listings},
    )


@router.get("/compare")
def compare_listings_page(
    request: Request,
    listing_ids: list[int] = Query(default=[]),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    listings = _fetch_user_listings(int(user["id"]))
    selected = _selected_listings(listings, listing_ids)
    error = None
    if listing_ids and len(selected) < 2:
        error = "Choose at least two listings to compare."
    elif len(selected) > 4:
        error = "Choose no more than four listings."

    return templates.TemplateResponse(
        "compare.html",
        {
            "request": request,
            "user": user,
            "listings": listings,
            "selected_listings": selected,
            "selected_ids": [listing["id"] for listing in selected],
            "destination": "",
            "commute_results": {},
            "travel_mode_labels": TRAVEL_MODE_LABELS,
            "error": error,
        },
    )


@router.post("/compare")
def calculate_comparison(
    request: Request,
    listing_ids: list[int] = Form(...),
    destination: str = Form(...),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    listings = _fetch_user_listings(int(user["id"]))
    selected = _selected_listings(listings, listing_ids)
    clean_destination = destination.strip()
    template_context = {
        "request": request,
        "user": user,
        "listings": listings,
        "selected_listings": selected,
        "selected_ids": [listing["id"] for listing in selected],
        "destination": clean_destination,
        "commute_results": {},
        "travel_mode_labels": TRAVEL_MODE_LABELS,
        "error": None,
    }

    if len(selected) < 2 or len(selected) > 4:
        template_context["error"] = "Choose between two and four listings."
        return templates.TemplateResponse("compare.html", template_context, status_code=400)

    if not clean_destination:
        template_context["error"] = "Enter the place you want to travel to."
        return templates.TemplateResponse("compare.html", template_context, status_code=400)

    try:
        destination_place = geocode_address(clean_destination)
    except GeospatialServiceError as exc:
        template_context["error"] = str(exc)
        return templates.TemplateResponse("compare.html", template_context, status_code=400)

    commute_results: dict[int, dict] = {}

    for listing in selected:
        listing_result = {"routes": {}, "error": None}
        commute_results[listing["id"]] = listing_result

        if not listing.get("location") or not listing.get("location_is_exact"):
            listing_result["error"] = "Exact listing location not available."
            continue

        try:
            latitude = listing.get("latitude")
            longitude = listing.get("longitude")

            if latitude is None or longitude is None:
                listing_place = geocode_address(listing["location"])
                latitude = listing_place.latitude
                longitude = listing_place.longitude

                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE listings
                            SET latitude = %s, longitude = %s,
                                geocoded_address = %s, updated_at = %s
                            WHERE id = %s AND user_id = %s
                            """,
                            (
                                latitude,
                                longitude,
                                listing_place.address,
                                datetime.utcnow().isoformat(),
                                listing["id"],
                                user["id"],
                            ),
                        )
                    conn.commit()

            for mode in TRAVEL_MODES:
                route = calculate_route(
                    float(latitude),
                    float(longitude),
                    destination_place.latitude,
                    destination_place.longitude,
                    mode,
                )
                listing_result["routes"][mode] = {
                    "distance_km": round(route.distance_metres / 1000, 1),
                    "duration_label": _duration_label(route.duration_seconds),
                }
        except GeospatialServiceError as exc:
            listing_result["error"] = str(exc)

    template_context["destination"] = destination_place.address
    template_context["commute_results"] = commute_results
    return templates.TemplateResponse("compare.html", template_context)


@router.get("/listings/{listing_id}")
def listing_detail_page(request: Request, listing_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM listings WHERE id = %s AND user_id = %s",
                (listing_id, user["id"]),
            )
            row = cur.fetchone()

    if not row:
        return RedirectResponse("/listings", status_code=303)

    listing = _listing_from_row(row)
    return templates.TemplateResponse(
        "listing_detail.html",
        {
            "request": request,
            "user": user,
            "listing": listing,
            "location_saved": request.query_params.get("location_saved"),
        },
    )


@router.post("/listings/{listing_id}/location")
def update_listing_location(
    request: Request,
    listing_id: int,
    location: str = Form(""),
    location_is_exact: str = Form("no"),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    clean_location = location.strip()
    exact_location = location_is_exact == "yes" and bool(clean_location)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE listings
                SET location = %s, location_is_exact = %s,
                    latitude = NULL, longitude = NULL, geocoded_address = NULL,
                    updated_at = %s
                WHERE id = %s AND user_id = %s
                """,
                (
                    clean_location,
                    exact_location,
                    datetime.utcnow().isoformat(),
                    listing_id,
                    user["id"],
                ),
            )
        conn.commit()

    return RedirectResponse(
        f"/listings/{listing_id}?location_saved=1",
        status_code=303,
    )
