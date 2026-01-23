# ScoreRent
Decision-support system that evaluates rental listings against renter profiles to reduce wasted application effort and costs.

## Description
ScoreRent is an informational decision-support tool that helps renters assess whether a rental listing is worth applying for. The system evaluates listings against a renter profile using affordability rules, documentation compatibility, application fee risk, and basic demand signals. The tool is rules-based and explainable; it does not predict acceptance outcomes.

## Features
- Rules-based evaluation producing:
  - score (0–100)
  - verdict (`WORTH_APPLYING`, `BORDERLINE`, `NOT_WORTH_IT`)
  - reasons (explainable output)
- Suggested monthly rent budget:
  - conservative (25% of income)
  - recommended (30% of income)
  - upper limit (35% of income)
- Document requirement evaluation using clusters:
  - worker: bank statement, payslip
  - new professional/recent graduate: employment contract, guarantor
  - student: proof of registration, proof of bursary, guarantor
- Universal penalty for missing bank statements (reflecting real-world rental application practices)
- Application fee risk weighting
- Two interfaces:
  - web UI (Jinja2)
  - REST API (FastAPI)

## Tech Stack
- Python
- FastAPI
- Pydantic
- Jinja2
- Uvicorn

## Project Structure
rentcheck/
├── main.py
├── evaluator.py
├── schemas.py
├── requirements.txt
├── templates/
│   └── index.html
└── static/
└── styles.css

## Setup
### Install dependencies

```bash
pip install -r requirements.txt

Run application

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

Access
	•	Web UI: http://127.0.0.1:8000/
	•	API Docs (Swagger): http://127.0.0.1:8000/docs

API

Endpoint

POST /evaluate

Example request

{
  "renter": {
    "monthly_income": 18000,
    "budget": 7000,
    "documents": ["employment_contract", "guarantor_letter"]
  },
  "listing": {
    "rent": 7500,
    "deposit": 7500,
    "application_fee": 850,
    "required_documents": ["bank_statement"],
    "area_demand": "HIGH"
  }
}

Example response

{
  "score": 48,
  "verdict": "NOT_WORTH_IT",
  "reasons": [
    "Rent exceeds stated budget",
    "Some required documents are missing, but alternative proof is available",
    "No bank statement provided (may reduce application strength)",
    "High demand area increases competition",
    "High application fee relative to budget",
    "Application fee increases cost of a low-confidence application"
  ],
  "suggested_budget": {
    "conservative": 4500,
    "recommended": 5400,
    "upper_limit": 6300
  }
}

## Design Notes
	•	The system is rules-based to ensure deterministic and explainable outputs.
	•	Listings are represented as structured user inputs instead of external integrations or scraping.
	•	Document clusters model common real-world application scenarios, but missing bank statements still apply a penalty for all applicant categories.

## Future Work
	•	Persist evaluations (database)
	•	Add listing templates / reusable profiles
	•	Add more configurable rule weights
	•	Add tests for evaluator rules

## Author
Built as a backend-focused portfolio project.

