import json
from datetime import datetime
from database import init_db

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
def on_startup():
    init_db()


def require_user(request: Request):
    user = get_current_user(request)
    return user


@app.get("/")
def home(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(
        "index.html", {"request": request, "user": user}
    )


@app.get("/signup")
def signup_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/profile", status_code=303)
    return templates.TemplateResponse("signup.html", {"request": request, "user": None, "error": None})


@app.post("/signup")
def signup_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    existing = get_user_by_email(email)
    if existing:
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "user": None, "error": "Email already registered."},
        )

    create_user(email, password)
    user = get_user_by_email(email)
    token = make_session_token(user["id"])
    resp = RedirectResponse("/profile", status_code=303)
    resp.set_cookie("session", token, httponly=True, samesite="lax")
    return resp


@app.get("/login")
def login_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/profile", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "user": None, "error": None})


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
            {"request": request, "user": None, "error": "Invalid email or password."},
        )

    token = make_session_token(user["id"])
    resp = RedirectResponse("/profile", status_code=303)
    resp.set_cookie("session", token, httponly=True, samesite="lax")
    return resp


@app.get("/logout")
def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie("session")
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

    profile_docs = []
    renter_type = "worker"
    monthly_income = 0

    if profile:
        renter_type = profile["renter_type"]
        monthly_income = int(profile["monthly_income"])
        profile_docs = json.loads(profile["docs_json"])

    docs_for_type = sorted(list(DOC_CLUSTERS.get(renter_type, set())))

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user,
            "renter_types": RENTER_TYPES,
            "renter_type": renter_type,
            "monthly_income": monthly_income,
            "docs": profile_docs,
            "docs_for_type": docs_for_type,
        },
    )


@app.post("/profile")
def profile_post(
    request: Request,
    renter_type: str = Form(...),
    monthly_income: int = Form(...),
    documents: str = Form(""),
):
    user = require_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    renter_type = renter_type.strip()
    if renter_type not in RENTER_TYPES:
        renter_type = "worker"

    docs = [d.strip().lower() for d in documents.split(",") if d.strip()]

    conn = get_conn()
    conn.execute(
        """
        INSERT INTO profiles (user_id, renter_type, monthly_income, docs_json, is_default, created_at)
        VALUES (?, ?, ?, ?, 1, ?)
        """,
        (user["id"], renter_type, int(monthly_income), json.dumps(docs), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    return RedirectResponse("/evaluate", status_code=303)


@app.get("/evaluate")
def evaluate_page(request: Request):
    user = require_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    conn = get_conn()
    profile = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user["id"],),
    ).fetchone()
    conn.close()

    if not profile:
        return RedirectResponse("/profile", status_code=303)

    return templates.TemplateResponse(
        "evaluate.html",
        {
            "request": request,
            "user": user,
            "profile": profile,
            "demand_levels": DEMAND_LEVELS,
        },
    )


@app.post("/evaluate")
def evaluate_post(
    request: Request,
    rent: int = Form(...),
    deposit: int = Form(...),
    application_fee: int = Form(...),
    area_demand: str = Form("MEDIUM"),
    required_documents: str = Form(""),
):
    user = require_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    conn = get_conn()
    profile = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user["id"],),
    ).fetchone()

    if not profile:
        conn.close()
        return RedirectResponse("/profile", status_code=303)

    renter_type = profile["renter_type"]
    monthly_income = int(profile["monthly_income"])
    renter_docs = json.loads(profile["docs_json"])

    required_docs = [d.strip().lower() for d in required_documents.split(",") if d.strip()]

    result, bands = evaluate(
        renter_type=renter_type,
        monthly_income=monthly_income,
        renter_docs=renter_docs,
        rent=int(rent),
        deposit=int(deposit),
        application_fee=int(application_fee),
        required_documents=required_docs,
        area_demand=area_demand,
    )

    listing = {
        "rent": int(rent),
        "deposit": int(deposit),
        "application_fee": int(application_fee),
        "required_documents": required_docs,
        "area_demand": area_demand,
    }

    conn.execute(
        """
        INSERT INTO evaluations (
            user_id, profile_id, listing_json, score, verdict, confidence,
            reasons_json, actions_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user["id"],
            profile["id"],
            json.dumps(listing),
            result.score,
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
            "ev": ev,
            "listing": listing,
            "reasons": reasons,
            "actions": actions,
        },
    )


@app.get("/history")
def history_page(request: Request):
    user = require_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    conn = get_conn()
    evals = conn.execute(
        "SELECT * FROM evaluations WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        (user["id"],),
    ).fetchall()
    conn.close()

    return templates.TemplateResponse(
        "history.html",
        {"request": request, "user": user, "evals": evals},
    )


@app.get("/compare")
def compare_page(request: Request):
    user = require_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    conn = get_conn()
    evals = conn.execute(
        "SELECT * FROM evaluations WHERE user_id = ? ORDER BY created_at DESC LIMIT 3",
        (user["id"],),
    ).fetchall()
    conn.close()

    items = []
    for ev in evals:
        listing = json.loads(ev["listing_json"])
        reasons = json.loads(ev["reasons_json"])
        items.append(
            {
                "id": ev["id"],
                "score": ev["score"],
                "verdict": ev["verdict"],
                "confidence": ev["confidence"],
                "rent": listing.get("rent"),
                "deposit": listing.get("deposit"),
                "application_fee": listing.get("application_fee"),
                "demand": listing.get("area_demand"),
                "top_reason": reasons[0] if reasons else "",
            }
        )

    return templates.TemplateResponse(
        "compare.html",
        {"request": request, "user": user, "items": items},
    )
