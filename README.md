![CI Tests](https://github.com/nonluthando/ScoreRent/actions/workflows/tests.yml/badge.svg)
# ScoreRent
Decision-support system that evaluates rental listings against renter profiles to reduce wasted application effort and costs.

## Description
ScoreRent is an informational decision-support tool that helps renters assess whether a rental listing is worth applying for. The system evaluates listings against a renter profile using affordability rules, documentation compatibility, application fee risk, and basic demand signals. The tool is rules-based and explainable; it does not predict acceptance outcomes.

## Features
Rules-based evaluation engine with explainable scoring output
- Suggested affordability bands based on renter income:
  - 25% (conservative)
  - 30% (recommended)
  - 35% (upper limit)
- Document evaluation:
  - required document mismatch detection
  - renter-type document clustering:
    - worker: bank statement, payslip
    - new professional: employment contract, guarantor letter
    - student: proof of registration, bursary letter, guarantor letter
  - universal penalty for missing bank statements
- Demand weighting (`LOW`, `MEDIUM`, `HIGH`) to reflect competition
- Guest mode (run evaluation without sign up)
- Logged-in mode with persistence:
  - renter profile saved
  - evaluation history saved
  - dashboard with latest evaluation
- Automated testing for evaluator logic with `pytest`
- CI using GitHub Actions

## Tech Stack
- Python
- FastAPI
- Jinja2 (server-rendered UI)
- Pydantic / typed data modelling
- PostgreSQL (persistence)
- psycopg3 (Postgres driver)
- pytest
- GitHub Actions (CI)
- Docker / devcontainer (Codespaces-ready local DB)

## Project Structure
```text
ScoreRent/
├── main.py
├── evaluator.py
├── auth.py
├── database.py
├── requirements.txt
├── ARCHITECTURE.md
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── signup.html
│   ├── login.html
│   ├── dashboard.html
│   ├── profile.html
│   ├── evaluate.html
│   ├── results.html
│   ├── guest_results.html
│   └── history.html
└── static/
    ├── styles.css
    └── script.js
```
## Running Locally 
### Install dependencies

```bash
pip install -r requirements.txt
```
### Configure Postgres
```bash
docker run --name scorerent-db \
  -e POSTGRES_USER=scorerent \
  -e POSTGRES_PASSWORD=scorerent \
  -e POSTGRES_DB=scorerent \
  -p 5432:5432 \
  -d postgres:16
```

### Run application
```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
### open: 
Web UI: http://127.0.0.1:8000/

## Running in GitHub Codespaces

This repo includes a devcontainer configuration. Postgres runs as a service via docker-compose.
	1.	Open Codespaces
	2.	Install requirements (if not automatically installed)
	3.	Run:
```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
## Evaluation Logic Summary

The evaluator is rules-based and explainable. Key scoring signals include:
	•	Affordability vs income (25/30/35% bands)
	•	Upfront cost risk (rent + deposit + application fee)
	•	Required document mismatch
	•	Renter-type document clustering
	•	Universal missing bank statement penalty
	•	Demand weighting (competition proxy)

The output includes both:
	•	reasons explaining the score/verdict
	•	actions recommending what to do next

See ARCHITECTURE.md for the full system design.

## Testing 
### Run tests locally:
```bash
pytest -q
```
### CI
CI runs automatically via GitHub Actions on push/PR and executes:
	•	pytest

A passing CI badge indicates evaluator rules are protected against regressions.


### Example response
```json
{
  "score": 62,
  "verdict": "BORDERLINE",
  "confidence": "MEDIUM",
  "reasons": [
    "Rent is above the recommended band (30% of income).",
    "Some required documents are missing.",
    "High demand area increases competition."
  ],
  "actions": [
    "If possible, reduce rent target closer to 30% of monthly income.",
    "Gather the missing required documents before applying.",
    "Consider adding a guarantor to strengthen your application."
  ],
  "suggested_budget": {
    "conservative": 4500,
    "recommended": 5400,
    "upper_limit": 6300
  }
}
```
## Design Notes
	•	The system is deterministic to ensure explainable outcomes.
	•	Data is stored as JSON snapshots to keep evaluations reproducible.
	•	Postgres is used instead of SQLite to support concurrency and avoid DB locking.


## Future Work
	•	More configurable rule weights
	•	Enhanced endpoint testing (FastAPI TestClient)
	•	Listing requirement extraction from text/screenshot (OCR/LLM parsing)

	

## Author
Luthando Mbuyane.
#### Built as a backend-focused portfolio project.

