![CI Tests](https://github.com/nonluthando/ScoreRent/actions/workflows/tests.yml/badge.svg)
# ScoreRent

ScoreRent helps you decide if a rental listing is worth applying for *before* you waste money on application fees.

It compares your renter profile to listing requirements and returns a confidence score (0 to 100) with a clear verdict:

- **Worth applying**
- **Borderline**
- **Not worth it**

The score is **not** a probability of acceptance. It is a confidence indicator based on affordability, documents, and demand.

## Why I built this

When I was applying for rentals for my final year of university, the process was expensive and frustrating. Application fees are often non refundable, and many listings reject people quickly for missing documents (like 3 month bank statements) or affordability issues.

This hit newly graduated renters and students especially hard, because many people simply cannot afford paying multiple application fees while trying to find a place urgently.

ScoreRent was built to make that process less wasteful.

## What it does

ScoreRent takes:
- your renter profile (worker / new professional / student)
- what documents you have
- a listing (rent, deposit, application fee, demand, required docs)

Then it outputs:
- a **confidence score (0 to 100)**
- a verdict (**Worth applying / Borderline / Not worth it**)
- the main reasons behind the result
- recommended actions (what to fix / what to upload / what to do next)
- an explainable breakdown showing how the score was calculated step by step

Guest users can evaluate instantly. Logged in users can save evaluations and view history.

## Features

### Guest mode
- Evaluate listings without creating an account
- Enter renter type + income/support + documents
- Student bursary toggle supported
- See reasons, actions, and breakdown instantly

### Logged in users
- Sign up / login
- Save renter profile (type, income, documents)
- Save evaluation history (persistent)
- View past evaluations

### Scoring engine
- Deterministic rules (same inputs always give the same output)
- Affordability based on rent to income bands
- Document fit checks
- Demand level weighting (LOW / MEDIUM / HIGH)
- Explainable breakdown:
  - each rule shows score change like `-30` and `70 → 40`
  - progress bar updates after every rule

### Engineering / reliability
- PostgreSQL persistence
- pytest unit tests for evaluator rules
- GitHub Actions CI runs tests on every push / PR
- Docker setup for reproducible development environment


## Tech stack

- **Python**
- **FastAPI**
- **Jinja2 templates**
- **PostgreSQL (psycopg)**
- **pytest**
- **GitHub Actions (CI)**
- **Docker + Docker Compose**
- Deployed on **Render**

## Screenshots (recommended)

Suggested screenshots to include:
- Home page
- Evaluation form (guest mode)
- Guest result output
- Breakdown section expanded (shows the scoring flow)
- Login page
- Evaluation history page

## How scoring works (high level)

ScoreRent uses rules based on:
- **Affordability** (dominant factor):
  - rent above recommended affordability gets penalised heavily
  - rent above affordability limit usually results in “not worth it”
- **Document fit**
  - missing listing required documents reduces confidence
  - worker applications require stronger income proof
  - new professional logic is lighter and supports employment contract alternatives
  - student logic supports bursary vs guarantor pathways
- **Demand**
  - high demand areas reduce confidence because competition is stronger

The goal is to model realistic decision-making that a letting agent might follow.


## Run locally

### Option 1: Docker (recommended)

Requirements:
- Docker
- Docker Compose

Run:

```bash
docker compose up --build
```
Then open:
	•	http://localhost:8000

### Option 2: Local Python + Postgres
Requirements:
	•	Python 3.11+
	•	PostgreSQL
	
1.	Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```
2.	Install dependencies:
```bash
python -m venv .venv
pip install -r requirements.txt
```
3. Setup database url:
```bash
export DATABASE_URL="postgresql://scorerent:scorerent@localhost:5432/scorerent"
```

4. Start app:
```bash
uvicorn main:app --reload
```
## CI
GitHub Actions runs:
	•	pytest
	•	coverage report generation

Every push and pull request to main triggers tests.


## Limitations
	•	The score is a confidence indicator. It does not guarantee acceptance.
	•	Rental requirements vary by landlord and agency. Rules are designed to be realistic and extendable, not universal truth.
	•	Student requirements are tricky because real processes differ (some listings accept students before registration). ScoreRent tries to surface these risks without assuming one single standard.

## Future Enhancements
	•	Better student accommodation flow (separate mode)
	•	Saved listings per user
	•	“Compare listings” view (side by side)
	•	Admin/rules page to tune penalties without code changes
	•	Export evaluation as a PDF report

## Author
Luthando Mbuyane

## Live demo: https://scorerent.onrender.com

