from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import (
    create_user,
    get_user_by_email,
    verify_password,
    make_session_token,
    get_current_user,
)

router = APIRouter()

templates = Jinja2Templates(
    directory="templates"
)


@router.get("/signup")
def signup_page(
    request: Request
):

    user = get_current_user(
        request
    )

    if user:

        return RedirectResponse(
            "/dashboard",
            status_code=303
        )

    return templates.TemplateResponse(
        "signup.html",
        {
            "request": request
        }
    )


@router.post("/signup")
def signup_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):

    if len(
        password.encode(
            "utf-8"
        )
    ) > 72:

        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "error":
                "Password too long."
            },
            status_code=400
        )

    existing = get_user_by_email(
        email
    )

    if existing:

        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "error":
                "Email already registered."
            },
            status_code=400
        )

    user_id = create_user(
        email,
        password
    )

    token = make_session_token(
        user_id
    )

    resp = RedirectResponse(
        "/dashboard",
        status_code=303
    )

    resp.set_cookie(
        "session",
        token,
        httponly=True,
        samesite="lax"
    )

    return resp


@router.get("/login")
def login_page(
    request: Request
):

    user = get_current_user(
        request
    )

    if user:

        return RedirectResponse(
            "/dashboard",
            status_code=303
        )

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request
        }
    )


@router.post("/login")
def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):

    user = get_user_by_email(
        email
    )

    if (
        not user
        or not verify_password(
            password,
            user["password_hash"]
        )
    ):

        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error":
                "Invalid email or password."
            },
            status_code=400
        )

    token = make_session_token(
        user["id"]
    )

    resp = RedirectResponse(
        "/dashboard",
        status_code=303
    )

    resp.set_cookie(
        "session",
        token,
        httponly=True,
        samesite="lax"
    )

    return resp


@router.get("/logout")
def logout():

    resp = RedirectResponse(
        "/",
        status_code=303
    )

    resp.delete_cookie(
        "session"
    )

    return resp
