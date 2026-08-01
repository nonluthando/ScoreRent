from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import get_current_user
from database import get_conn

router = APIRouter(tags=["saved listings"])
templates = Jinja2Templates(directory="templates")


def _clean_list(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def _load_json(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


@router.post("/listings")
def save_listing(
    request: Request,
    listing_name: str = Form(""),
    location: str = Form(""),
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
    title = listing_name.strip() or (f"Listing in {clean_location}" if clean_location else f"Listing (R{rent})")
    upfront_cost = int(rent) + int(deposit) + int(application_fee)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO listings (
                    user_id, title, location, monthly_rent, deposit,
                    application_fee, upfront_cost, area_demand,
                    required_documents_json, amenities_json, pros_json,
                    cons_json, source_url, notes, created_at, updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    user["id"], title, location.strip(), int(rent), int(deposit),
                    int(application_fee), upfront_cost, area_demand,
                    json.dumps(_clean_list(required_documents)),
                    json.dumps(_clean_list(amenities_text.splitlines())),
                    json.dumps(_clean_list(pros_text.splitlines())),
                    json.dumps(_clean_list(cons_text.splitlines())),
                    source_url.strip(), notes.strip(),
                    datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
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

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM listings
                WHERE user_id = %s
                ORDER BY updated_at DESC
                """,
                (user["id"],),
            )
            rows = cur.fetchall()

    listings = []
    for row in rows:
        item = dict(row)
        item["amenities"] = _load_json(item.pop("amenities_json"), [])
        item["pros"] = _load_json(item.pop("pros_json"), [])
        item["cons"] = _load_json(item.pop("cons_json"), [])
        listings.append(item)

    return templates.TemplateResponse(
        "listings.html",
        {"request": request, "user": user, "listings": listings},
    )


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

            cur.execute(
                """
                SELECT * FROM saved_destinations
                WHERE user_id = %s
                ORDER BY label ASC
                """,
                (user["id"],),
            )
            destinations = cur.fetchall()

            cur.execute(
                """
                SELECT lc.*, sd.label AS destination_label, sd.address AS destination_address
                FROM listing_commutes lc
                JOIN saved_destinations sd ON sd.id = lc.destination_id
                WHERE lc.listing_id = %s AND lc.user_id = %s
                ORDER BY sd.label ASC, lc.travel_mode ASC
                """,
                (listing_id, user["id"]),
            )
            commutes = cur.fetchall()

    if not row:
        return RedirectResponse("/listings", status_code=303)

    listing = dict(row)
    listing["required_documents"] = _load_json(listing.pop("required_documents_json"), [])
    listing["amenities"] = _load_json(listing.pop("amenities_json"), [])
    listing["pros"] = _load_json(listing.pop("pros_json"), [])
    listing["cons"] = _load_json(listing.pop("cons_json"), [])

    commute_items = []
    for commute in commutes:
        item = dict(commute)
        item["distance_km"] = round(item["distance_metres"] / 1000, 1)
        total_minutes = max(1, round(item["duration_seconds"] / 60))
        item["duration_minutes"] = total_minutes
        item["duration_label"] = (
            f"{total_minutes // 60} hr {total_minutes % 60} min"
            if total_minutes >= 60
            else f"{total_minutes} min"
        )
        commute_items.append(item)

    return templates.TemplateResponse(
        "listing_detail.html",
        {
            "request": request,
            "user": user,
            "listing": listing,
            "destinations": destinations,
            "commutes": commute_items,
            "commute_error": request.query_params.get("commute_error"),
            "commute_success": request.query_params.get("commute_success"),
        },
    )
