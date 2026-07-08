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

    return templates.TemplateResponse("signup.html", {"request": request})


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

    return templates.TemplateResponse("login.html", {"request": request})


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


@router.get("/profile")
def profile_page(request: Request):
    current_user = require_authenticated_user(request)

    if not current_user:
        return RedirectResponse("/login", status_code=303)

    user_profile = get_latest_profile_for_user(current_user["id"])
    profile_defaults = profile_to_defaults(user_profile)

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": current_user,
            "profile": user_profile,
            "renter_type": profile_defaults["renter_type"],
            "monthly_income": profile_defaults["monthly_income"],
            "is_bursary_student": profile_defaults["is_bursary_student"],
            "docs_selected": profile_defaults["submitted_documents"],
            "doc_clusters": {
                key: sorted(list(value))
                for key, value in REQUIRED_DOCUMENT_CLUSTERS.items()
            },
        },
    )


@router.post("/profile")
def save_profile(
    request: Request,
    renter_type: str = Form(...),
    monthly_income: int = Form(...),
    submitted_documents: list[str] = Form([]),
    is_bursary_student: str = Form("no"),
):
    current_user = require_authenticated_user(request)

    if not current_user:
        return RedirectResponse("/login", status_code=303)

    renter_type = (renter_type or "worker").strip().lower()

    submitted_documents = [
        document.strip().lower()
        for document in submitted_documents
        if document and document.strip()
    ]

    is_bursary_student = is_bursary_student == "yes"

    db_connection = get_conn()
    db_cursor = db_connection.cursor()

    db_cursor.execute(
        """
        INSERT INTO profiles (
            user_id,
            renter_type,
            monthly_income,
            is_bursary_student,
            documents_json,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            current_user["id"],
            renter_type,
            int(monthly_income),
            is_bursary_student,
            json.dumps(submitted_documents),
            datetime.utcnow().isoformat(),
        ),
    )

    db_connection.commit()

    db_cursor.close()
    db_connection.close()

    return RedirectResponse("/evaluate", status_code=303)


@router.get("/evaluate")
def rental_evaluation_page(request: Request):
    current_user = get_current_user(request)

    profile_defaults = {
        "renter_type": "worker",
        "monthly_income": 0,
        "submitted_documents": [],
        "is_bursary_student": False,
    }

    if current_user:
        user_profile = get_latest_profile_for_user(current_user["id"])
        profile_defaults = profile_to_defaults(user_profile)

    return templates.TemplateResponse(
        "evaluate.html",
        {
            "request": request,
            "user": current_user,
            "renter_type": profile_defaults["renter_type"],
            "monthly_income": profile_defaults["monthly_income"],
            "renter_docs": profile_defaults["submitted_documents"],
            "is_bursary_student": profile_defaults["is_bursary_student"],
            "doc_clusters": {
                key: sorted(list(value))
                for key, value in REQUIRED_DOCUMENT_CLUSTERS.items()
            },
            "demand_levels": [level.value for level in DemandLevel],
        },
    )


@router.post("/evaluate")
def evaluate_rental_listing(
    request: Request,
    listing_name: str = Form(""),
    rent: int = Form(...),
    deposit: int = Form(...),
    application_fee: int = Form(...),
    area_demand: str = Form("MEDIUM"),
    required_documents: list[str] = Form([]),
    guest_renter_type: str = Form("worker"),
    guest_monthly_income: int = Form(0),
    guest_submitted_documents: list[str] = Form([]),
    guest_guarantor_monthly_income: int = Form(0),
    student_is_bursary: str = Form("no"),
):
    current_user = get_current_user(request)

    renter_type = "worker"
    monthly_income = 0
    submitted_documents: list[str] = []
    guarantor_monthly_income = 0
    is_bursary_student = False

    profile_id = None
    user_id = None

    if current_user:
        user_id = current_user["id"]
        user_profile = get_latest_profile_for_user(current_user["id"])
        profile_defaults = profile_to_defaults(user_profile)

        if user_profile:
            profile_id = user_profile["id"]

        renter_type = profile_defaults["renter_type"]
        monthly_income = profile_defaults["monthly_income"]
        submitted_documents = profile_defaults["submitted_documents"]
        is_bursary_student = profile_defaults["is_bursary_student"]

    else:
        renter_type = (guest_renter_type or "worker").strip().lower()
        monthly_income = int(guest_monthly_income or 0)

        submitted_documents = [
            document.strip().lower()
            for document in guest_submitted_documents
            if document and document.strip()
        ]

        guarantor_monthly_income = int(guest_guarantor_monthly_income or 0)
        is_bursary_student = student_is_bursary == "yes"

    required_documents = [
        document.strip().lower()
        for document in required_documents
        if document and document.strip()
    ]

    evaluation_result, recommended_budget_bands = evaluate_rental_application(
        renter_type=renter_type,
        monthly_income=int(monthly_income),
        submitted_documents=submitted_documents,
        monthly_rent=int(rent),
        security_deposit=int(deposit),
        application_fee=int(application_fee),
        required_documents=required_documents,
        area_demand=area_demand,
        guarantor_monthly_income=int(guarantor_monthly_income),
        is_bursary_student=is_bursary_student,
    )

    listing_snapshot = {
        "listing_name": listing_name.strip(),
        "rent": int(rent),
        "deposit": int(deposit),
        "application_fee": int(application_fee),
        "required_documents": required_documents,
        "area_demand": area_demand,
        "guarantor_monthly_income": int(guarantor_monthly_income),
        "breakdown": evaluation_result.breakdown,
    }

    if not current_user:
        return templates.TemplateResponse(
            "guest_results.html",
            {
                "request": request,
                "user": None,
                "listing": listing_snapshot,
                "result": evaluation_result,
                "bands": recommended_budget_bands,
                "guest": True,
            },
        )

    if not listing_name.strip():
        listing_name = f"Listing (R{rent})"

    db_connection = get_conn()
    db_cursor = db_connection.cursor()

    db_cursor.execute(
        """
        INSERT INTO evaluations (
            user_id,
            profile_id,
            listing_name,
            listing_json,
            score,
            verdict,
            confidence,
            reasons_json,
            actions_json,
            created_at
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        RETURNING id
        """,
        (
            user_id,
            profile_id,
            listing_name.strip(),
            json.dumps(listing_snapshot),
            int(evaluation_result.score),
            evaluation_result.verdict,
            evaluation_result.confidence,
            json.dumps(evaluation_result.reasons),
            json.dumps(evaluation_result.actions),
            datetime.utcnow().isoformat(),
        ),
    )

    evaluation_id = db_cursor.fetchone()["id"]

    db_connection.commit()

    db_cursor.close()
    db_connection.close()

    return RedirectResponse(f"/results/{evaluation_id}", status_code=303)


@router.get("/results/{evaluation_id}")
def evaluation_results_page(request: Request, evaluation_id: int):
    current_user = require_authenticated_user(request)

    if not current_user:
        return RedirectResponse("/login", status_code=303)

    db_connection = get_conn()
    db_cursor = db_connection.cursor()

    db_cursor.execute(
        """
        SELECT *
        FROM evaluations
        WHERE id = %s
        AND user_id = %s
        """,
        (evaluation_id, current_user["id"]),
    )

    evaluation_record = db_cursor.fetchone()

    db_cursor.close()
    db_connection.close()

    if not evaluation_record:
        return RedirectResponse("/history", status_code=303)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "user": current_user,
            "evaluation": evaluation_record,
            "listing": load_json_field(evaluation_record["listing_json"], {}),
            "reasons": load_json_field(evaluation_record["reasons_json"], []),
            "actions": load_json_field(evaluation_record["actions_json"], []),
        },
    )


@router.get("/compare")
def compare_evaluations_page(request: Request):
    current_user = require_authenticated_user(request)

    if not current_user:
        return RedirectResponse("/login", status_code=303)

    db_connection = get_conn()
    db_cursor = db_connection.cursor()

    db_cursor.execute(
        """
        SELECT
            id,
            listing_name,
            score,
            verdict,
            confidence,
            listing_json,
            reasons_json,
            created_at
        FROM evaluations
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 3
        """,
        (current_user["id"],),
    )

    evaluation_rows = db_cursor.fetchall()

    db_cursor.close()
    db_connection.close()

    items = []

    for row in evaluation_rows:
        listing = load_json_field(row["listing_json"], {})
        reasons = load_json_field(row["reasons_json"], [])

        items.append(
            {
                "id": row["id"],
                "listing_name": row["listing_name"] or "Unnamed listing",
                "score": row["score"],
                "verdict": row["verdict"],
                "confidence": row["confidence"],
                "rent": listing.get("rent", 0),
                "deposit": listing.get("deposit", 0),
                "application_fee": listing.get("application_fee", 0),
                "demand": listing.get("area_demand", "MEDIUM"),
                "top_reason": reasons[0] if reasons else "No reason available",
                "created_at": row["created_at"],
            }
        )

    return templates.TemplateResponse(
        "compare.html",
        {
            "request": request,
            "user": current_user,
            "items": items,
        },
    )


@router.get("/history")
def evaluation_history_page(request: Request):
    current_user = require_authenticated_user(request)

    if not current_user:
        return RedirectResponse("/login", status_code=303)

    db_connection = get_conn()
    db_cursor = db_connection.cursor()

    db_cursor.execute(
        """
        SELECT
            id,
            listing_name,
            score,
            verdict,
            confidence,
            created_at
        FROM evaluations
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (current_user["id"],),
    )

    evaluation_history = db_cursor.fetchall()

    db_cursor.close()
    db_connection.close()

    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "user": current_user,
            "evaluations": evaluation_history,
        },
    )
@router.get("/learn")
def learn_page(request: Request):
    return templates.TemplateResponse(
        "learn.html",
        {
            "request": request,
            "user": get_current_user(request),
        },
    )


@router.get("/learn/rent-affordability")
def learn_affordability_page(request: Request):
    return templates.TemplateResponse(
        "learn_affordability.html",
        {
            "request": request,
            "user": get_current_user(request),
        },
    )


@router.get("/learn/documents-landlords-ask-for")
def learn_documents_page(request: Request):
    return templates.TemplateResponse(
        "learn_documents.html",
        {
            "request": request,
            "user": get_current_user(request),
        },
    )


@router.get("/learn/improve-application")
def learn_improve_application_page(request: Request):
    return templates.TemplateResponse(
        "learn_improve.html",
        {
            "request": request,
            "user": get_current_user(request),
        },
    )


@router.get("/learn/rental-red-flags")
def learn_red_flags_page(request: Request):
    return templates.TemplateResponse(
        "learn_red_flags.html",
        {
            "request": request,
            "user": get_current_user(request),
        },
    )
