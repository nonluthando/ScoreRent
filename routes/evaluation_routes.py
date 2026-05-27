import json

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

from evaluator import (
    evaluate,
)

from engine.config import (
    DOC_CLUSTERS,
    DEMAND_LEVELS,
)

from services.profile_service import (
    get_latest_profile,
)

from services.result_service import (
    get_result,
)

from services.evaluation_service import (

    create_listing_payload,

    build_guest_result,

    insert_evaluation,

    default_listing_name,
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
# Results page
# ---------------------------------------------------------

@router.get(
    "/results/{evaluation_id}"
)
def results_page(
    request: Request,

    evaluation_id: int,
):
    """
    Display evaluation results.
    """

    user = require_user(
        request
    )

    if not user:

        return RedirectResponse(
            "/login",
            status_code=303,
        )

    result = get_result(
        evaluation_id,
        user["id"],
    )

    if not result:

        return RedirectResponse(
            "/history",
            status_code=303,
        )

    return templates.TemplateResponse(

    "results.html",

    {

        "request":
            request,

        "user":
            user,

        "evaluation":
            result[
                "evaluation"
            ],

        "listing":
            result[
                "listing"
            ],

        "reasons":
            result[
                "reasons"
            ],

        "actions":
            result[
                "actions"
            ],

        "bands":
            result[
                "bands"
            ],
    },
)

# ---------------------------------------------------------
# Evaluation page
# ---------------------------------------------------------

@router.get(
    "/evaluate"
)
def evaluate_page(
    request: Request,
):
    """
    Evaluation form.
    """

    user = get_current_user(
        request
    )

    renter_type = "worker"

    monthly_income = 0

    renter_docs = []

    is_bursary_student = False

    if user:

        profile = get_latest_profile(
            user["id"]
        )

        if profile:

            renter_type = profile[
                "renter_type"
            ]

            monthly_income = int(
                profile[
                    "monthly_income"
                ]
            )

            renter_docs = json.loads(
                profile[
                    "documents_json"
                ]
            )

            is_bursary_student = bool(
                profile.get(
                    "is_bursary_student",
                    False,
                )
            )

    return templates.TemplateResponse(

        "evaluate.html",

        {

            "request":
                request,

            "user":
                user,

            "renter_type":
                renter_type,

            "monthly_income":
                monthly_income,

            "renter_docs":
                renter_docs,

            "is_bursary_student":
                is_bursary_student,

            "doc_clusters":

                {
                    k:
                    sorted(
                        list(v)
                    )

                    for k, v

                    in DOC_CLUSTERS.items()
                },

            "demand_levels":
                DEMAND_LEVELS,
        },
    )


# ---------------------------------------------------------
# Run evaluation
# ---------------------------------------------------------

@router.post(
    "/evaluate"
)
def evaluate_post(

    request: Request,

    listing_name: str = Form(""),

    rent: int = Form(...),

    deposit: int = Form(...),

    application_fee: int = Form(...),

    area_demand: str = Form(
        "MEDIUM"
    ),

    required_documents:
    list[str] = Form([]),
):
    """
    Execute evaluation.
    """

    user = get_current_user(
        request
    )

    renter_type = "worker"

    monthly_income = 0

    renter_docs = []

    profile_id = None

    user_id = None

    if user:

        profile = get_latest_profile(
            user["id"]
        )

        if profile:

            profile_id = profile[
                "id"
            ]

            user_id = user[
                "id"
            ]

            renter_type = profile[
                "renter_type"
            ]

            monthly_income = int(
                profile[
                    "monthly_income"
                ]
            )

            renter_docs = json.loads(
                profile[
                    "documents_json"
                ]
            )

    result, bands = evaluate(

        renter_type=
            renter_type,

        monthly_income=
            monthly_income,

        renter_docs=
            renter_docs,

        rent=rent,

        deposit=deposit,

        application_fee=
            application_fee,

        required_documents=
            required_documents,

        area_demand=
            area_demand,
    )

    listing = create_listing_payload(

        listing_name=
            listing_name,

        rent=rent,

        deposit=deposit,

        application_fee=
            application_fee,

        required_documents=
            required_documents,

        area_demand=
            area_demand,

        guarantor_monthly_income=0,

        breakdown=
            result.breakdown,

        budget_bands=
            bands,
    )

    if not user:

        guest = build_guest_result(
            listing,
            result,
            bands,
        )

        return templates.TemplateResponse(

            "guest_results.html",

            {

                "request":
                    request,

                **guest,
            },
        )

    listing_name = default_listing_name(
        listing_name,
        rent,
    )

    evaluation_id = insert_evaluation(

        user_id=
            user_id,

        profile_id=
            profile_id,

        listing_name=
            listing_name,

        listing=
            listing,

        result=
            result,
    )

    return RedirectResponse(

        f"/results/{evaluation_id}",

        status_code=303,
    )
