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

from services.auth_service import (

    register_user,

    authenticate,
)

router = APIRouter()

templates = Jinja2Templates(
    directory="templates"
)


# ---------------------------------------------------------
# Signup page
# ---------------------------------------------------------

@router.get(
    "/signup"
)
def signup_page(
    request: Request,
):
    """
    Signup page.
    """

    user = get_current_user(
        request
    )

    if user:

        return RedirectResponse(
            "/dashboard",
            status_code=303,
        )

    return templates.TemplateResponse(

        "signup.html",

        {
            "request":
                request,
        },
    )


# ---------------------------------------------------------
# Signup submit
# ---------------------------------------------------------

@router.post(
    "/signup"
)
def signup_post(

    request: Request,

    email: str = Form(...),

    password: str = Form(...),
):
    """
    Register user.
    """

    result = register_user(
        email,
        password,
    )

    if not result[
        "success"
    ]:

        return templates.TemplateResponse(

            "signup.html",

            {

                "request":
                    request,

                "error":
                    result[
                        "error"
                    ],
            },

            status_code=400,
        )

    resp = RedirectResponse(
        "/dashboard",
        status_code=303,
    )

    resp.set_cookie(

        "session",

        result[
            "token"
        ],

        httponly=True,

        samesite="lax",
    )

    return resp


# ---------------------------------------------------------
# Login page
# ---------------------------------------------------------

@router.get(
    "/login"
)
def login_page(
    request: Request,
):
    """
    Login page.
    """

    user = get_current_user(
        request
    )

    if user:

        return RedirectResponse(
            "/dashboard",
            status_code=303,
        )

    return templates.TemplateResponse(

        "login.html",

        {
            "request":
                request,
        },
    )


# ---------------------------------------------------------
# Login submit
# ---------------------------------------------------------

@router.post(
    "/login"
)
def login_post(

    request: Request,

    email: str = Form(...),

    password: str = Form(...),
):
    """
    Authenticate user.
    """

    result = authenticate(
        email,
        password,
    )

    if not result[
        "success"
    ]:

        return templates.TemplateResponse(

            "login.html",

            {

                "request":
                    request,

                "error":
                    result[
                        "error"
                    ],
            },

            status_code=400,
        )

    resp = RedirectResponse(
        "/dashboard",
        status_code=303,
    )

    resp.set_cookie(

        "session",

        result[
            "token"
        ],

        httponly=True,

        samesite="lax",
    )

    return resp


# ---------------------------------------------------------
# Logout
# ---------------------------------------------------------

@router.get(
    "/logout"
)
def logout():
    """
    Destroy session.
    """

    resp = RedirectResponse(
        "/",
        status_code=303,
    )

    resp.delete_cookie(
        "session"
    )

    return resp
