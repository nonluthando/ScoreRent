import json
from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import (
    create_user,
    get_current_user,
    get_user_by_email,
    make_session_token,
    verify_password,
)

from database import get_conn

from evaluator import (
    DemandLevel,
    REQUIRED_DOCUMENT_CLUSTERS,
    evaluate_rental_application,
)


router = APIRouter()
templates = Jinja2Templates(directory="templates")


def load_json_field(value, fallback=None):
    if fallback is None:
        fallback = {}

    if value is None:
        return fallback

    if isinstance(value, (dict, list)):
        return value

    return json.loads(value)


def get_latest_profile_for_user(user_id: int):
    db_connection = get_conn()
    db_cursor = db_connection.cursor()

    db_cursor.execute(
        """
        SELECT *
        FROM profiles
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id,),
    )

    profile = db_cursor.fetchone()

    db_cursor.close()
    db_connection.close()

    return profile


def profile_to_defaults(profile):
    defaults = {
        "renter_type": "worker",
        "monthly_income": 0,
        "submitted_documents": [],
        "is_bursary_student": False,
    }

    if not profile:
        return defaults

    defaults["renter_type"] = profile["renter_type"]
    defaults["monthly_income"] = int(profile["monthly_income"])
    defaults["submitted_documents"] = load_json_field(
        profile["documents_json"],
        [],
    )
    defaults["is_bursary_student"] = bool(
        profile.get("is_bursary_student", False)
    )

    return defaults


def require_authenticated_user(request: Request):
    return get_current_user(request)


@router.get("/")
def home_page(request: Request):
    current_user = get_current_user(request)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": current_user,
        },
    )


@router.get("/dashboard")
def dashboard_page(request: Request):
    current_user = require_authenticated_user(request)

    if not current_user:
        return RedirectResponse("/login", status_code=303)

    db_connection = get_conn()
    db_cursor = db_connection.cursor()

    db_cursor.execute(
        """
        SELECT *
        FROM evaluations
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (current_user["id"],),
    )

    latest_evaluation = db_cursor.fetchone()

    db_cursor.close()
    db_connection.close()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "last_eval": latest_evaluation,
        },
    )


@router.get("/signup")
def signup_page(request: Request):
    current_user = get_current_user(request)

    if current_user:
        return RedirectResponse("/dashboard", status_code=303)

    return templates.TemplateResponse(
        "signup.html",
        {"request": request},
    )


@router.post("/signup")
def create_account(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    email = email.strip().lower()

    if len(password.encode("utf-8")) > 72:
        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "error": "Password too long (max 72 bytes).",
            },
            status_code=400,
        )

    existing_user = get_user_by_email(email)

    if existing_user:
        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "error": "Email already registered. Please log in instead.",
            },
            status_code=400,
        )

    user_id = create_user(email, password)
    session_token = make_session_token(user_id)

    response = RedirectResponse("/dashboard", status_code=303)

    response.set_cookie(
        "session",
        session_token,
        httponly=True,
        samesite="lax",
    )

    return response


@router.get("/login")
def login_page(request: Request):
    current_user = get_current_user(request)

    if current_user:
        return RedirectResponse("/dashboard", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {"request": request},
    )


@router.post("/login")
def authenticate_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    email = email.strip().lower()

    existing_user = get_user_by_email(email)

    if (
        not existing_user
        or not verify_password(password, existing_user["password_hash"])
    ):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid email or password.",
            },
            status_code=400,
        )

    session_token = make_session_token(existing_user["id"])

    response = RedirectResponse("/dashboard", status_code=303)

    response.set_cookie(
        "session",
        session_token,
        httponly=True,
        samesite="lax",
    )

    return response


@router.get("/logout")
def logout_user(request: Request):
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("session")
    return response
