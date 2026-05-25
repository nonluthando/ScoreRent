import json
from datetime import datetime

from fastapi import (
    APIRouter,
    Request,
    Form,
)

from fastapi.responses import (
    RedirectResponse,
)

from fastapi.templating import (
    Jinja2Templates,
)

from auth import (
    get_current_user,
)

from engine.config import (
    DOC_CLUSTERS,
)

from database import (
    get_conn,
)

from services.profile_service import (
    get_latest_profile,
    normalize_profile,
)

router = APIRouter()

templates = Jinja2Templates(
    directory="templates"
)


def require_user(
    request: Request,
):
    """
    Require authenticated user.
    """

    return get_current_user(
        request
    )


# ---------------------------------------------------------
# GET profile
# ---------------------------------------------------------

@router.get(
    "/profile"
)
def profile_page(
    request: Request,
):
    """
    Profile page.
    """

    user = require_user(
        request
    )

    if not user:

        return RedirectResponse(
            "/login",
            status_code=303,
        )

    profile = (
        get_latest_profile(
            user["id"]
        )
    )

    profile_data = (
        normalize_profile(
            profile
        )
    )

    return templates.TemplateResponse(

        "profile.html",

        {

            "request":
                request,

            "user":
                user,

            "profile":
                profile,

            "renter_type":
                profile_data[
                    "renter_type"
                ],

            "monthly_income":
                profile_data[
                    "monthly_income"
                ],

            "is_bursary_student":
                profile_data[
                    "is_bursary_student"
                ],

            "docs_selected":
                profile_data[
                    "docs_selected"
                ],

            "doc_clusters":

                {
                    k:
                    sorted(
                        list(v)
                    )

                    for k, v

                    in DOC_CLUSTERS.items()
                },
        },
    )


# ---------------------------------------------------------
# POST profile
# ---------------------------------------------------------

@router.post(
    "/profile"
)
def profile_post(

    request: Request,

    renter_type: str = Form(...),

    monthly_income: int = Form(...),

    renter_docs:
    list[str] = Form([]),

    is_bursary_student:
    str = Form("no"),
):
    """
    Save renter profile.
    """

    user = require_user(
        request
    )

    if not user:

        return RedirectResponse(
            "/login",
            status_code=303,
        )

    renter_type = (
        renter_type
        .strip()
        .lower()
    )

    renter_docs = [

        d.strip().lower()

        for d in renter_docs

        if d and d.strip()
    ]

    bursary = (
        is_bursary_student
        == "yes"
    )

    conn = get_conn()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO profiles(

                    user_id,

                    renter_type,

                    monthly_income,

                    is_bursary_student,

                    documents_json,

                    created_at

                )

                VALUES(

                    %s,

                    %s,

                    %s,

                    %s,

                    %s,

                    %s
                )
                """,

                (

                    user["id"],

                    renter_type,

                    monthly_income,

                    bursary,

                    json.dumps(
                        renter_docs
                    ),

                    datetime.utcnow(
                    ).isoformat(),
                ),
            )

            conn.commit()

    finally:

        conn.close()

    return RedirectResponse(
        "/evaluate",
        status_code=303,
    )
