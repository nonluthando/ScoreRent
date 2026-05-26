# ScoreRent Architecture

## Overview

ScoreRent is a rules-based decision-support web application that evaluates rental listings against renter profiles. It generates explainable scores, recommendation verdicts, confidence levels, reasons, actions, and budget guidance to help renters avoid spending money on low-confidence applications.

The system is intentionally deterministic rather than ML-based to prioritise transparency, explainability, reproducibility, and predictable behaviour.

The backend was refactored from a more monolithic structure into separated route, service, schema, and evaluation layers to improve maintainability and testing.

## High-Level Architecture

```text
Web Layer
├── Routes
├── Services
├── Evaluator
├── Persistence
└── Schemas
```

## Project Structure

```text
scorerent/
├── routes/
├── services/
├── schemas/
├── evaluator.py
├── database/
├── templates/
└── tests/
```

## Web Layer

FastAPI + Jinja2 handle routing, templates, authentication, profile flows, evaluation submission, dashboards, and history views.

## Service Layer

- evaluation_service.py
- profile_service.py
- history_service.py

Responsibilities:
- orchestration
- persistence coordination
- history retrieval
- response preparation

## Evaluator

Outputs:
- score
- verdict
- confidence
- reasons
- actions
- budget guidance

Rules:
- affordability thresholds
- document validation
- demand weighting
- recommendation logic

## Schemas

Validation models:

- requests
- responses
- history
- summaries
- pagination

## Persistence

PostgreSQL stores:

- users
- profiles
- evaluations
- snapshots

## Authentication

Uses:

- passlib
- bcrypt
- itsdangerous
- signed cookies

## Testing

pytest + GitHub Actions

Coverage:
- affordability
- penalties
- demand weighting
- verdict mapping
- boundary tests

## Future Improvements

- UX improvements
- Alembic
- logging
- metrics
- rate limiting
- CSRF
- analytics
- LLM extraction
