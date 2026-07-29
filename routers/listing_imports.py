from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import get_current_user
from evaluator import DOCUMENT_ALIASES, DemandLevel
from services.listing_import_service import (
    ListingImportError,
    extract_listing_from_api,
    extraction_to_template_data,
    validate_and_prepare_images,
)


router = APIRouter(tags=["listing imports"])
templates = Jinja2Templates(directory="templates")

IMPORT_LIMIT = 5
IMPORT_WINDOW_SECONDS = 60 * 60
_import_attempts: dict[int, deque[float]] = defaultdict(deque)
_rate_limit_lock = asyncio.Lock()


def _all_required_documents() -> list[str]:
    return sorted(DOCUMENT_ALIASES.keys())


async def _check_import_rate_limit(user_id: int) -> None:
    now = time.monotonic()
    cutoff = now - IMPORT_WINDOW_SECONDS

    async with _rate_limit_lock:
        attempts = _import_attempts[user_id]
        while attempts and attempts[0] < cutoff:
            attempts.popleft()

        if len(attempts) >= IMPORT_LIMIT:
            raise ListingImportError(
                "You have reached the screenshot-import limit. Try again in about an hour."
            )

        attempts.append(now)


@router.get("/import-listing")
def import_listing_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        "import_listing.html",
        {"request": request, "user": user, "error": None},
    )


@router.post("/import-listing")
async def import_listing_screenshots(
    request: Request,
    images: list[UploadFile] = File(...),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    try:
        await _check_import_rate_limit(int(user["id"]))
        prepared_images = await validate_and_prepare_images(images)
        extraction = await extract_listing_from_api(prepared_images)
    except ListingImportError as exc:
        status_code = 429 if "limit" in str(exc).lower() else 400
        return templates.TemplateResponse(
            "import_listing.html",
            {"request": request, "user": user, "error": str(exc)},
            status_code=status_code,
        )

    return templates.TemplateResponse(
        "confirm_listing_import.html",
        {
            "request": request,
            "user": user,
            "extraction": extraction_to_template_data(extraction),
            "demand_levels": [level.value for level in DemandLevel],
            "available_documents": _all_required_documents(),
        },
    )
