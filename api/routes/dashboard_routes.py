from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import get_current_user
from services.dashboard_service import build_dashboard

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


@router.get(
    "/dashboard"
)
def dashboard(
    request: Request,
):
    """
    Dashboard page.
    """

    user = require_user(
        request
    )

    if not user:

        return RedirectResponse(
            "/login",
            status_code=303,
        )

    dashboard_data = (
        build_dashboard(
            user["id"]
        )
    )

    return templates.TemplateResponse(

        "dashboard.html",

        {

            "request":
                request,

            "user":
                user,

            "last_eval":
                dashboard_data[
                    "last_eval"
                ],
        },
    )
