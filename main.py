import json
from datetime import datetime

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from database import init_db, get_conn
from auth import (
    create_user,
    get_user_by_email,
    verify_password,
    make_session_token,
    get_current_user,
)

from evaluator import evaluate, DOC_CLUSTERS, RENTER_TYPES, DEMAND_LEVELS

app = FastAPI(title="ScoreRent")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def startup():
    init_db()


def require_user(request: Request):
    return get_current_user(request)


@app.get("/")
def home(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "user": user},
    )


@app.get("/dashboard")
def dashboard(request: Request):
    user = require_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    conn = get_conn()
    last_eval = conn.execute(
        """
        SELECT * FROM evaluations
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user["id"],),
    ).fetchone()
    conn.close()

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "last_eval": last_eval},
    )


@app.get("/signup")
def signup_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/dashboard", status_code=303)

    return templates.TemplateResponse("signup.html", {"request": request})


@app.post("/signup")
def signup_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    if len(password.encode("utf-8")) > 72:
        # avoid bcrypt crash
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "Password too long (max 72 bytes)."},
            status_code=400,
        )

    existing = get_user_by_email(email)
    if existing:
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "Email already registered."},
            status_code=400,
        )

    user_id = create_user(email, password)
    token = make_session_token(user_id)

    resp = RedirectResponse("/dashboard", status_code=303)
    resp.set_cookie("session_token", token, httponly=True)
    return resp


@app.get("/login")
def login_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/dashboard", status_code=303)

    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password."},
            status_code=400,
        )

    token = make_session_token(user["id"])
    resp = RedirectResponse("/dashboard", status_code=303)
    resp.set_cookie("session_token", token, httponly=True)
    return resp


@app.get("/logout")
def logout(request: Request):
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie("session_token")
    return resp


@app.get("/profile")
def profile_page(request: Request):
    user = require_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    conn = get_conn()
    profile = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user["id"],),
    ).fetchone()
    conn.close()

    docs_selected = []
    renter_type = "worker"
    monthly_income = 0

    if profile:
        docs_selected = json.loads(profile["documents_json"])
        renter_type = profile["renter_type"]
        monthly_income = profile["monthly_income"]

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user,
            "profile": profile,
            "renter_type": renter_type,
            "monthly_income": monthly_income,
            "docs_selected": docs_selected,
            "doc_clusters": {k: sorted(list(v)) for k, v in DOC_CLUSTERS.items()},
        },
    )


@app.post("/profile")
def profile_post(
    request: Request,
    renter_type: str = Form(...),
    monthly_income: int = Form(...),
    renter_docs: list[str] = Form([]),  # ✅ checkbox support
):
    user = require_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    renter_docs = [d.strip().lower() for d in renter_docs if d.strip()]

    conn = get_conn()
    conn.execute(
        """
        INSERT INTO profiles (user_id, renter_type, monthly_income, documents_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user["id"],
            renter_type,
            int(monthly_income),
            json.dumps(renter_docs),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    return RedirectResponse("/evaluate", status_code=303)


@app.get("/evaluate")
def evaluate_page(request: Request):
    """
    ✅ Guest mode: allow everyone to evaluate.
    If logged in, profile is loaded automatically.
    """
    user = get_current_user(request)

    renter_type = "worker"
    monthly_income = 0
    renter_docs = []

    if user:
        conn = get_conn()
        profile = conn.execute(
            "SELECT * FROM profiles WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user["id"],),
        ).fetchone()
        conn.close()

        if profile:
            renter_type = profile["renter_type"]
            monthly_income = profile["monthly_income"]
            renter_docs = json.loads(profile["documents_json"])

    return templates.TemplateResponse(
        "evaluate.html",
        {
            "request": request,
            "user": user,
            "renter_type": renter_type,
            "monthly_income": monthly_income,
            "renter_docs": renter_docs,
            "doc_clusters": {k: sorted(list(v)) for k, v in DOC_CLUSTERS.items()},
            "demand_levels": DEMAND_LEVELS,
        },
    )


@app.post("/evaluate")
def evaluate_post(
    request: Request,
    listing_name: str = Form(""),
    rent: int = Form(...),
    deposit: int = Form(...),
    application_fee: int = Form(...),
    area_demand: str = Form("MEDIUM"),
    required_documents: list[str] = Form([]),  # ✅ checkbox support
):
    user = get_current_user(request)

    # Load profile if logged in (else guest must supply defaults)
    renter_type = "worker"
    monthly_income = 0
    renter_docs: list[str] = []

    profile_id = None
    user_id = None

    if user:
        user_id = user["id"]

        conn = get_conn()
        profile = conn.execute(
            "SELECT * FROM profiles WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user["id"],),
        ).fetchone()

        if profile:
            profile_id = profile["id"]
            renter_type = profile["renter_type"]
            monthly_income = int(profile["monthly_income"])
            renter_docs = json.loads(profile["documents_json"])

        conn.close()

    required_docs = [d.strip().lower() for d in required_documents if d.strip()]

    result, bands = evaluate(
        renter_type=renter_type,
        monthly_income=int(monthly_income),
        renter_docs=renter_docs,
        rent=int(rent),
        deposit=int(deposit),
        application_fee=int(application_fee),
        required_documents=required_docs,
        area_demand=area_demand,
    )

    listing = {
        "listing_name": listing_name.strip(),
        "rent": int(rent),
        "deposit": int(deposit),
        "application_fee": int(application_fee),
        "required_documents": required_docs,
        "area_demand": area_demand,
    }

    # ✅ Guest mode: show result immediately, don't store DB
    if not user:
        return templates.TemplateResponse(
            "guest_results.html",
            {
                "request": request,
                "user": None,
                "listing": listing,
                "result": result,
                "bands": bands,
                "guest": True,
            },
        )

    # Logged in: save evaluation
    if not listing_name.strip():
        listing_name = f"Listing (R{rent})"

    conn = get_conn()
    conn.execute(
        """
        INSERT INTO evaluations (
            user_id, profile_id, listing_name, listing_json, score, verdict, confidence,
            reasons_json, actions_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            profile_id,
            listing_name.strip(),
            json.dumps(listing),
            int(result.score),
            result.verdict,
            result.confidence,
            json.dumps(result.reasons),
            json.dumps(result.actions),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()

    eval_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.close()

    return RedirectResponse(f"/results/{eval_id}", status_code=303)


@app.get("/results/{evaluation_id}")
def results_page(request: Request, evaluation_id: int):
    user = require_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    conn = get_conn()
    ev = conn.execute(
        "SELECT * FROM evaluations WHERE id = ? AND user_id = ?",
        (evaluation_id, user["id"]),
    ).fetchone()
    conn.close()

    if not ev:
        return RedirectResponse("/history", status_code=303)

    listing = json.loads(ev["listing_json"])
    reasons = json.loads(ev["reasons_json"])
    actions = json.loads(ev["actions_json"])

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "user": user,
            "evaluation": ev,
            "listing": listing,
            "reasons": reasons,
            "actions": actions,
        },
    )


@app.get("/history")
def history(request: Request):
    user = require_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, listing_name, score, verdict, confidence, created_at
        FROM evaluations
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user["id"],),
    ).fetchall()
    conn.close()

    return templates.TemplateResponse(
        "history.html",
        {"request": request, "user": user, "evaluations": rows},
    )
