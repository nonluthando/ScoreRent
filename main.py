from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from schemas import EvaluationRequest
from evaluator import evaluate

app = FastAPI(
    title="RentCheck",
    description="Informational decision-support tool for rental applications",
    version="1.0.0"
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/evaluate")
def evaluate_ui(
    request: Request,
    monthly_income: int = Form(...),
    budget: int = Form(...),
    documents: str = Form(...),
    rent: int = Form(...),
    deposit: int = Form(...),
    application_fee: int = Form(...),
    required_documents: str = Form(...),
    area_demand: str = Form(...)
):
    renter = {
        "monthly_income": monthly_income,
        "budget": budget,
        "documents": [d.strip() for d in documents.split(",")]
    }

    listing = {
        "rent": rent,
        "deposit": deposit,
        "application_fee": application_fee,
        "required_documents": [d.strip() for d in required_documents.split(",")],
        "area_demand": area_demand
    }

    score, verdict, reasons = evaluate(
        renter=type("Obj", (), renter),
        listing=type("Obj", (), listing)
    )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": {
                "score": score,
                "verdict": verdict,
                "reasons": reasons
            }
        }
    )
