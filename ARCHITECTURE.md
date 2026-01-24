# ScoreRent Architecture

## Overview
ScoreRent is a rules-based decision-support web application that evaluates rental listings against a renter profile. It produces an explainable score (0–100), a verdict, and clear reasons/actions to help users avoid wasting application fees and effort on low-confidence listings.

The system is intentionally deterministic (not ML-based) to ensure transparency and predictable outcomes.

## High-Level Components

### 1) Web Layer (FastAPI + Jinja2)
The web layer handles:
- rendering pages (Jinja2 templates)
- form input collection and validation
- session-based authentication (cookies)
- persistence of profiles and evaluations

Key routes:
- `GET /` → homepage
- `GET/POST /signup` → create account
- `GET/POST /login` → authenticate
- `GET /dashboard` → last evaluation overview
- `GET/POST /profile` → renter profile setup
- `GET/POST /evaluate` → run evaluation
- `GET /results/{id}` → view saved result
- `GET /history` → list past evaluations

Templates:
- `index.html`, `login.html`, `signup.html`
- `profile.html`, `evaluate.html`
- `dashboard.html`, `history.html`, `results.html`, `guest_results.html`


### 2) Business Logic Layer (Evaluator)
The evaluator is the core decision engine.
It compares renter inputs and listing requirements using deterministic rules, producing:
- `score` (0–100)
- `verdict`: `WORTH_APPLYING | BORDERLINE | NOT_WORTH_IT`
- `confidence`: `HIGH | MEDIUM | LOW`
- `reasons`: explainable justification
- `actions`: suggested next steps
- suggested rent budget bands (25/30/35%)

Core signals:
- affordability thresholds (35% upper limit rule)
- upfront cost risk (rent + deposit + application fee)
- required-document mismatch
- renter-type document clustering
- universal bank statement penalty
- demand weighting (LOW/MEDIUM/HIGH)

The evaluator is isolated in `evaluator.py`, making it testable with `pytest`.


### 3) Persistence Layer (Postgres)
Postgres provides reliable storage for:
- users
- renter profiles
- saved evaluations/history

Data model:
- `users` → account data (hashed password)
- `profiles` → renter context snapshots (docs + income + type)
- `evaluations` → listing snapshot + evaluation result

Design choice:
- renter documents and listing inputs are stored as JSON blobs to keep schema simple
- the stored JSON snapshots make evaluations reproducible and auditable

## Authentication Design
Auth is implemented using:
- `passlib` + `bcrypt` for password hashing
- signed session cookies via `itsdangerous`

Session flow:
1. User logs in
2. Server generates signed token containing `user_id`
3. Token is stored in cookie `session` (`HttpOnly`, `SameSite=Lax`)
4. On every request, `get_current_user()` decodes token → loads user from DB

This provides lightweight session handling without server-side session storage.

## Data Flow (Request Lifecycle)

### Logged-in Evaluation Flow
1. User loads `/evaluate`
2. Server loads latest profile from DB (income, renter type, docs)
3. User submits listing input
4. Server calls `evaluate(...)`
5. Result is stored in DB
6. User is redirected to `/results/{evaluation_id}`

### Guest Evaluation Flow
1. User submits evaluation without authentication
2. Server computes evaluation
3. Result is rendered immediately
4. No data is stored


## Testing Strategy
Testing focuses on evaluator correctness:
- affordability rule penalties
- bank statement universal penalty
- demand weighting
- application fee logic behaviour
- boundary score → verdict mapping

CI (GitHub Actions) runs tests on each push/PR to prevent regressions.

## Future Improvements
- Focus more on UX/UI to prioritise user-centred design principles  
- Add Alembic for formal migrations
- Use a normalized schema for documents (if analytics needed)
- Add structured logging and metrics
- Add rate-limiting and CSRF protections
- Add listing text parsing (LLM extraction) to auto-fill requirements
- Add deployment configuration 
