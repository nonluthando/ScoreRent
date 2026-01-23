from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List

from schemas import EvaluationRequest, EvaluationResponse
from evaluator import evaluate

app = FastAPI(
    title="RentCheck",
    description="Informational decision-support tool for rental applications",
    version="1.1.0"
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# -------------------------
# UI ROUTES
# -------------------------

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/evaluate-ui")
def evaluate_ui(
    request: Request,

    # renter
    monthly_income: int = Form(...),
    budget: int = Form(...),
    documents: List[str] = Form([]),

    # listing
    rent: int = Form(...),
    deposit: int = Form(...),
    application_fee: int = Form(...),
    required_documents: List[str] = Form([]),
    area_demand: str = Form(...)
):
    renter = type("Obj", (), {
        "monthly_income": monthly_income,
        "budget": budget,
        "documents": documents
    })

    listing = type("Obj", (), {
        "rent": rent,
        "deposit": deposit,
        "application_fee": application_fee,
        "required_documents": required_documents,
        "area_demand": area_demand
    })

    score, verdict, reasons, suggested = evaluate(renter, listing)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": {
                "score": score,
                "verdict": verdict,
                "reasons": reasons,
                "suggested_budget": suggested
            }
        }
    )


# -------------------------
# API ROUTE (JSON)
# -------------------------

@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate_api(payload: EvaluationRequest):
    score, verdict, reasons, suggested = evaluate(payload.renter, payload.listing)

    return {
        "score": score,
        "verdict": verdict,
        "reasons": reasons,
        "suggested_budget": suggested
    }
