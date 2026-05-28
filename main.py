import json
from datetime import datetime

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api import router as api_router

from auth import (
    create_user,
    get_current_user,
    get_user_by_email,
    make_session_token,
    verify_password,
)

from database import get_conn, init_db

from evaluator import (
    DemandLevel,
    REQUIRED_DOCUMENT_CLUSTERS,
    evaluate_rental_application,
)


app = FastAPI(title="ScoreRent")

templates = Jinja2Templates(directory="templates")

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

app.include_router(api_router)


# ============================================================
# Application Startup
# ============================================================

@app.on_event("startup")
def initialize_application():
    """
    Initialize database tables during application startup.
    """

    init_db()


# ============================================================
# Authentication Helpers
# ============================================================

def require_authenticated_user(request: Request):
    """
    Retrieve currently authenticated user from session.
    """

    return get_current_user(request)


# ============================================================
# Home Routes
# ============================================================

@app.get("/")
def home_page(request: Request):
    """
    Render application landing page.
    """

    current_user = get_current_user(request)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": current_user,
        },
    )


@app.get("/dashboard")
def dashboard_page(request: Request):
    """
    Render authenticated user dashboard.
    """

    current_user = require_authenticated_user(request)

    if not current_user:
        return RedirectResponse(
            "/login",
            status_code=303,
        )

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


# ============================================================
# Signup Routes
# ============================================================

@app.get("/signup")
def signup_page(request: Request):
    """
    Render signup page.
    """

    current_user = get_current_user(request)

    if current_user:
        return RedirectResponse(
            "/dashboard",
            status_code=303,
        )

    return templates.TemplateResponse(
        "signup.html",
        {"request": request},
    )


@app.post("/signup")
def create_account(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    """
    Create new user account.
    """

    # bcrypt maximum supported length
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
                "error": "Email already registered.",
            },
            status_code=400,
        )

    user_id = create_user(email, password)

    session_token = make_session_token(user_id)

    response = RedirectResponse(
        "/dashboard",
        status_code=303,
    )

    response.set_cookie(
        "session",
        session_token,
        httponly=True,
        samesite="lax",
    )

    return response


# ============================================================
# Login Routes
# ============================================================

@app.get("/login")
def login_page(request: Request):
    """
    Render login page.
    """

    current_user = get_current_user(request)

    if current_user:
        return RedirectResponse(
            "/dashboard",
            status_code=303,
        )

    return templates.TemplateResponse(
        "login.html",
        {"request": request},
    )


@app.post("/login")
def authenticate_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    """
    Authenticate existing user.
    """

    existing_user = get_user_by_email(email)

    if (
        not existing_user
        or not verify_password(
            password,
            existing_user["password_hash"],
        )
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

    response = RedirectResponse(
        "/dashboard",
        status_code=303,
    )

    response.set_cookie(
        "session",
        session_token,
        httponly=True,
        samesite="lax",
    )

    return response


@app.get("/logout")
def logout_user(request: Request):
    """
    Logout authenticated user.
    """

    response = RedirectResponse(
        "/",
        status_code=303,
    )

    response.delete_cookie("session")

    return response


# ============================================================
# Profile Routes
# ============================================================

@app.get("/profile")
def profile_page(request: Request):
    """
    Render renter profile page.
    """

    current_user = require_authenticated_user(request)

    if not current_user:
        return RedirectResponse(
            "/login",
            status_code=303,
        )

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
        (current_user["id"],),
    )

    user_profile = db_cursor.fetchone()

    db_cursor.close()
    db_connection.close()

    selected_documents = []

    renter_type = "worker"

    monthly_income = 0

    is_bursary_student = False

    if user_profile:

        selected_documents = json.loads(
            user_profile["documents_json"]
        )

        renter_type = user_profile["renter_type"]

        monthly_income = user_profile["monthly_income"]

        is_bursary_student = bool(
            user_profile.get("is_bursary_student", False)
        )

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": current_user,
            "profile": user_profile,
            "renter_type": renter_type,
            "monthly_income": monthly_income,
            "is_bursary_student": is_bursary_student,
            "docs_selected": selected_documents,
            "doc_clusters": {
                key: sorted(list(value))
                for key, value in REQUIRED_DOCUMENT_CLUSTERS.items()
            },
        },
    )


@app.post("/profile")
def save_profile(
    request: Request,
    renter_type: str = Form(...),
    monthly_income: int = Form(...),
    submitted_documents: list[str] = Form([]),
    is_bursary_student: str = Form("no"),
):
    """
    Save renter profile information.
    """

    current_user = require_authenticated_user(request)

    if not current_user:
        return RedirectResponse(
            "/login",
            status_code=303,
        )

    renter_type = (
        renter_type or "worker"
    ).strip().lower()

    submitted_documents = [
        document.strip().lower()
        for document in submitted_documents
        if document and document.strip()
    ]

    is_bursary_student = (
        is_bursary_student == "yes"
    )

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

    return RedirectResponse(
        "/evaluate",
        status_code=303,
    )


# ============================================================
# Evaluation Routes
# ============================================================

@app.get("/evaluate")
def rental_evaluation_page(request: Request):
    """
    Render rental evaluation page.
    """

    current_user = get_current_user(request)

    renter_type = "worker"

    monthly_income = 0

    submitted_documents: list[str] = []

    is_bursary_student = False

    if current_user:

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
            (current_user["id"],),
        )

        user_profile = db_cursor.fetchone()

        db_cursor.close()
        db_connection.close()

        if user_profile:

            renter_type = user_profile["renter_type"]

            monthly_income = int(
                user_profile["monthly_income"]
            )

            submitted_documents = json.loads(
                user_profile["documents_json"]
            )

            is_bursary_student = bool(
                user_profile.get(
                    "is_bursary_student",
                    False,
                )
            )

    return templates.TemplateResponse(
        "evaluate.html",
        {
            "request": request,
            "user": current_user,
            "renter_type": renter_type,
            "monthly_income": monthly_income,
            "renter_docs": submitted_documents,
            "is_bursary_student": is_bursary_student,
            "doc_clusters": {
                key: sorted(list(value))
                for key, value in REQUIRED_DOCUMENT_CLUSTERS.items()
            },
            "demand_levels": [
                level.value
                for level in DemandLevel
            ],
        },
    )


@app.post("/evaluate")
def evaluate_rental_listing(
    request: Request,

    listing_name: str = Form(""),

    rent: int = Form(...),

    deposit: int = Form(...),

    application_fee: int = Form(...),

    area_demand: str = Form("MEDIUM"),

    required_documents: list[str] = Form([]),

    # Guest evaluation fields
    guest_renter_type: str = Form("worker"),

    guest_monthly_income: int = Form(0),

    guest_submitted_documents: list[str] = Form([]),

    guest_guarantor_monthly_income: int = Form(0),

    student_is_bursary: str = Form("no"),
):
    """
    Evaluate rental listing affordability and approval likelihood.
    """

    current_user = get_current_user(request)

    renter_type = "worker"

    monthly_income = 0

    submitted_documents: list[str] = []

    guarantor_monthly_income = 0

    is_bursary_student = False

    profile_id = None

    user_id = None

    # ========================================================
    # Authenticated User Flow
    # ========================================================

    if current_user:

        user_id = current_user["id"]

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
            (current_user["id"],),
        )

        user_profile = db_cursor.fetchone()

        if user_profile:

            profile_id = user_profile["id"]

            renter_type = user_profile["renter_type"]

            monthly_income = int(
                user_profile["monthly_income"]
            )

            submitted_documents = json.loads(
                user_profile["documents_json"]
            )

            is_bursary_student = bool(
                user_profile.get(
                    "is_bursary_student",
                    False,
                )
            )

        db_cursor.close()
        db_connection.close()

    # ========================================================
    # Guest Evaluation Flow
    # ========================================================

    else:

        renter_type = (
            guest_renter_type or "worker"
        ).strip().lower()

        monthly_income = int(
            guest_monthly_income or 0
        )

        submitted_documents = [
            document.strip().lower()
            for document in guest_submitted_documents
            if document and document.strip()
        ]

        guarantor_monthly_income = int(
            guest_guarantor_monthly_income or 0
        )

        is_bursary_student = (
            student_is_bursary == "yes"
        )

    required_documents = [
        document.strip().lower()
        for document in required_documents
        if document and document.strip()
    ]

    # ========================================================
    # Run Evaluation Engine
    # ========================================================

    (
        evaluation_result,
        recommended_budget_bands,
    ) = evaluate_rental_application(
        renter_type=renter_type,
        monthly_income=int(monthly_income),
        submitted_documents=submitted_documents,
        monthly_rent=int(rent),
        security_deposit=int(deposit),
        application_fee=int(application_fee),
        required_documents=required_documents,
        area_demand=area_demand,
        guarantor_monthly_income=int(
            guarantor_monthly_income
        ),
        is_bursary_student=is_bursary_student,
    )

    listing_snapshot = {
        "listing_name": listing_name.strip(),
        "rent": int(rent),
        "deposit": int(deposit),
        "application_fee": int(application_fee),
        "required_documents": required_documents,
        "area_demand": area_demand,
        "guarantor_monthly_income": int(
            guarantor_monthly_income
        ),
        "breakdown": evaluation_result.breakdown,
    }

    # ========================================================
    # Guest Results
    # ========================================================

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

    # ========================================================
    # Persist Evaluation
    # ========================================================

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
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
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

    return RedirectResponse(
        f"/results/{evaluation_id}",
        status_code=303,
    )


# ============================================================
# Results Routes
# ============================================================

@app.get("/results/{evaluation_id}")
def evaluation_results_page(
    request: Request,
    evaluation_id: int,
):
    """
    Render evaluation results page.
    """

    current_user = require_authenticated_user(request)

    if not current_user:
        return RedirectResponse(
            "/login",
            status_code=303,
        )

    db_connection = get_conn()
    db_cursor = db_connection.cursor()

    db_cursor.execute(
        """
        SELECT *
        FROM evaluations
        WHERE id = %s
        AND user_id = %s
        """,
        (
            evaluation_id,
            current_user["id"],
        ),
    )

    evaluation_record = db_cursor.fetchone()

    db_cursor.close()
    db_connection.close()

    if not evaluation_record:
        return RedirectResponse(
            "/history",
            status_code=303,
        )

    listing_snapshot = json.loads(
        evaluation_record["listing_json"]
    )

    evaluation_reasons = json.loads(
        evaluation_record["reasons_json"]
    )

    evaluation_actions = json.loads(
        evaluation_record["actions_json"]
    )

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "user": current_user,
            "evaluation": evaluation_record,
            "listing": listing_snapshot,
            "reasons": evaluation_reasons,
            "actions": evaluation_actions,
        },
    )


# ============================================================
# History Routes
# ============================================================

@app.get("/history")
def evaluation_history_page(request: Request):
    """
    Render authenticated user's evaluation history.
    """

    current_user = require_authenticated_user(request)

    if not current_user:
        return RedirectResponse(
            "/login",
            status_code=303,
        )

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
