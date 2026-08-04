![CI Tests](https://github.com/nonluthando/ScoreRent/actions/workflows/tests.yml/badge.svg)

# ScoreRent

Rules-based rental decision-support platform helping renters evaluate listings before spending money on rental applications.

**Live Demo:** https://scorerent.onrender.com

ScoreRent compares renter profiles against listing requirements and produces:

- Explainable score (0–100)
- Recommendation verdict
- Confidence level
- Reasons behind results
- Suggested actions
- Budget guidance

The system is intentionally **deterministic rather than ML-based** to prioritise transparency, explainability, and predictable behaviour.

---

# Why I Built This

When I was applying for rentals during my final year at university, the process was expensive and frustrating.

Application fees are often non-refundable, and many listings reject applicants quickly because of affordability issues or missing documentation such as bank statements and proof of income.

This affects students, recent graduates, and first-time renters especially hard because multiple unsuccessful applications become expensive very quickly.

ScoreRent was built to help reduce wasted applications and support better decisions before paying fees.

---

# Features

## Guest Mode

Guests can evaluate listings immediately without creating an account.

Supported inputs include:

- Renter type
- Income / support information
- Documents
- Bursary support
- Listing requirements
- Deposit
- Demand level

Outputs include:

- Score
- Verdict
- Confidence
- Reasons
- Actions
- Breakdown view

No information is stored.

---

## Authenticated Users

Users can:

- Create accounts
- Login
- Save renter profiles
- Store evaluations
- View history
- Revisit previous recommendations

Stored profile information includes:

- Income
- Renter type
- Documents
- Support details
- Guarantor information

---

## Decision Engine

ScoreRent evaluates:

- Affordability
- Deposit burden
- Application fees
- Required documents
- Demand level
- Supporting documentation
- Renter pathways

Example:

```text
Score: 78

Verdict:
WORTH_APPLYING

Confidence:
HIGH

Reasons:
✓ Affordable rent range
✓ Strong document fit
✓ Lower upfront risk

Actions:
- Proceed with application
- Upload remaining documents
```

Results include:

- Score explanation
- Rule breakdown
- Suggested actions
- Confidence indicators
- Budget guidance

---

# Tech Stack

### Backend

- Python
- FastAPI
- Jinja2

### Persistence

- PostgreSQL (psycopg)

### Authentication

- passlib
- bcrypt
- signed cookies
- itsdangerous

### Testing

- pytest
- GitHub Actions

### Deployment

- Docker
- Docker Compose
- Render

---

# Architecture

ScoreRent follows a layered backend design using separated routes, services, schemas, evaluation logic, and persistence layers.

Detailed architecture documentation:

[ScoreRent_Architecture.md](./ScoreRent_Architecture.md)

The project was later refactored after commercial Laravel experience, applying production-inspired separation patterns and translating them into FastAPI.

Refactor highlights:

- Route separation
- Service layer introduction
- Schema organisation
- Cleaner responsibility ownership
- Improved testing boundaries

---

# Evaluation Logic (High Level)

## Affordability

Primary factor.

Rules include:

- Rent-to-income analysis
- Budget recommendations
- Affordability bands
- Upper affordability thresholds

---

## Financial Risk

Evaluates:

- Deposit burden
- Application fees
- Upfront costs

Higher risk lowers confidence.

---

## Documentation

Checks include:

- Required documents
- Missing items
- Student pathways
- Guarantor support
- Bursary support
- Worker requirements

---

## Demand

Demand weighting:

```text
LOW
MEDIUM
HIGH
```

Higher demand reduces confidence because competition increases.

---

# Testing

Testing focuses on evaluator correctness.

Covered scenarios:

- Affordability penalties
- Demand weighting
- Application fees
- Document validation
- Boundary scores
- Verdict mapping
- Confidence behaviour

Run locally:

```bash
pytest
```

CI runs automatically through GitHub Actions on:

- Push
- Pull Request

---

# Run Locally

## Option 1 — Docker (Recommended)

Requirements:

- Docker
- Docker Compose

Run:

```bash
docker compose up --build
```

Open:

```text
http://localhost:8000
```

---

## Option 2 — Python + PostgreSQL

Requirements:

- Python 3.11+
- PostgreSQL

Create environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure database:

```bash
export DATABASE_URL="postgresql://scorerent:scorerent@localhost:5432/scorerent"
```

Run application:

```bash
uvicorn main:app --reload
```

---

# Limitations

- Score is a confidence indicator rather than acceptance probability
- Rules aim to be realistic but are not universal
- Rental processes differ between landlords and agencies
- Student accommodation processes vary significantly

The goal is decision support rather than prediction.

---

# Future Improvements

Planned work:

- Accessibility improvements
- UX refinement
- Student accommodation mode
- Compare listings feature
- PDF exports
- Structured logging
- Metrics
- Alembic migrations
- Rate limiting
- CSRF protection
- Listing extraction workflows
- LLM-assisted requirement parsing

---

# What I Learned

ScoreRent became my strongest example of learning beyond coursework.

The project started as an independent backend application and later evolved after commercial software engineering experience.

Following work in a Laravel production environment, I revisited the system and refactored it by introducing:

- Route separation
- Service layers
- Schemas
- Cleaner architecture
- Improved testing boundaries

This process strengthened my ability to transfer architectural ideas across technologies and improve systems iteratively.

---

# Author

**Luthando Mbuyane**

GitHub: https://github.com/nonluthando

Portfolio: https://nonluthando.github.io/portfolio-v2

Live Demo: https://scorerent.onrender.com

## Listing screenshot import

ScoreRent can send up to four rental-listing screenshots directly to the Gemini API and show an editable confirmation page before running the normal rules-based evaluator. Gemini extracts listing facts only; it never calculates the ScoreRent score or verdict.

### Configure Gemini

1. Create an API key in Google AI Studio.
2. Add `GEMINI_API_KEY` to the ScoreRent service environment variables.
3. Optionally set `GEMINI_MODEL`; the default is `gemini-2.5-flash-lite`.
4. Redeploy ScoreRent.

The import feature is available to authenticated users at `/import-listing`.

### Privacy boundary

Images are validated and resized in memory, sent directly from the ScoreRent backend to Gemini, and not written to ScoreRent's database. The prompt excludes contact details from the returned data. Users must review all extracted values before the existing deterministic evaluator runs.

For free-tier Gemini API usage, submitted content may be used by Google to improve its products. Use synthetic or non-sensitive screenshots during portfolio testing, and clearly disclose this before accepting public uploads.

## Screenshot import configuration

Set these environment variables on Render:

```text
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-2.5-flash-lite
```

Screenshot imports are limited to five attempts per signed-in user per hour per app instance. Users should crop out personal information before upload because screenshots are sent to Google Gemini.

## Safe test database

Database-backed tests require a dedicated database whose name contains `test`:

```bash
export TEST_DATABASE_URL=postgresql://user:password@localhost:5432/scorerent_test
pytest
```

Without `TEST_DATABASE_URL`, pure unit tests still run and database-backed tests are skipped. The test suite will refuse to clean a database whose name does not contain `test`.

## Saved listings

Authenticated users can now save imported listings with costs, location, required documents,
amenities, factual pros and cons, source links, and personal notes. The database table is created
on application startup. Imported information must still be reviewed before it is saved.

## Listing comparison and travel time

Authenticated users can select two to four saved listings and compare rent, upfront costs,
amenities, pros, and potential downsides side by side. They enter one workplace, campus,
or other destination on the comparison page, and ScoreRent calculates driving, walking,
and cycling estimates for every selected listing with a confirmed exact location.

1. Create a Geoapify project and copy its API key.
2. Add `GEOAPIFY_API_KEY` to the Render environment.
3. Redeploy the service.
4. Import and save listings, confirm exact addresses where available, then choose **Compare**.

Suburb-only or approximate locations remain usable for normal listing comparison, but travel
calculations are withheld until the user confirms a full address or uniquely identifiable building.
Public-transport routing is intentionally excluded from the first version because schedule coverage
and reliability vary by location.
