from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import get_current_user
from services.history_service import get_history

router = APIRouter()

templates = Jinja2Templates(
    directory="templates"
)


def require_user(
    request: Request,
):
    return get_current_user(
        request
    )


@router.get(
    "/history"
)
def history(
    request: Request,
):
    """
    Evaluation history page.
    """

    user = require_user(
        request
    )

    if not user:

        return RedirectResponse(
            "/login",
            status_code=303,
        )

    evaluations = (
        get_history(
            user["id"]
        )
    )

    return templates.TemplateResponse(

        "history.html",

        {

            "request":
                request,

            "user":
                user,

            "evaluations":
                evaluations,
        },
    )
