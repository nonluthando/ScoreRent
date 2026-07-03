import os

import pytest
from fastapi.testclient import TestClient

# ------------------------------------------------------------------
# Test Environment
# ------------------------------------------------------------------

os.environ["DATABASE_URL"] = (
    os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://scorerent:scorerent@test-db:5432/scorerent_test",
    )
)

os.environ.setdefault(
    "SECRET_KEY",
    "test-secret-key",
)

from database import get_conn, init_db
from main import app


# ------------------------------------------------------------------
# Shared Test Client
# ------------------------------------------------------------------

@pytest.fixture(scope="session")
def client():
    """
    Shared FastAPI test client.
    """
    return TestClient(app)


# ------------------------------------------------------------------
# Database Setup
# ------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    Create tables before running tests.
    """
    init_db()
    yield


@pytest.fixture(autouse=True)
def clean_database():
    """
    Remove all persisted data before every test.
    """

    conn = get_conn()

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM evaluations")
            cur.execute("DELETE FROM profiles")
            cur.execute("DELETE FROM users")

        conn.commit()

    finally:
        conn.close()

    yield


# ------------------------------------------------------------------
# Shared Evaluation Payloads
# ------------------------------------------------------------------

@pytest.fixture
def worker_payload():
    return {
        "renter_type": "worker",
        "monthly_income": 30000,
        "submitted_documents": [
            "bank statement",
            "payslip",
        ],
        "monthly_rent": 8000,
        "security_deposit": 8000,
        "application_fee": 0,
        "required_documents": [],
        "area_demand": "MEDIUM",
    }


@pytest.fixture
def student_payload():
    return {
        "renter_type": "student",
        "monthly_income": 9000,
        "submitted_documents": [
            "nsfas award letter",
        ],
        "monthly_rent": 7000,
        "security_deposit": 7000,
        "application_fee": 0,
        "required_documents": [],
        "area_demand": "MEDIUM",
        "is_bursary_student": True,
    }


# ------------------------------------------------------------------
# Assertion Helpers
# ------------------------------------------------------------------

def assert_reason_contains(result, text):
    assert any(
        text.lower() in reason.lower()
        for reason in result.reasons
    ), (
        f"Expected reason containing '{text}'. "
        f"Got {result.reasons}"
    )


def assert_action_contains(result, text):
    assert any(
        text.lower() in action.lower()
        for action in result.actions
    ), (
        f"Expected action containing '{text}'. "
        f"Got {result.actions}"
    )


def assert_score_range(result, minimum, maximum):
    assert minimum <= result.score <= maximum, (
        f"Expected score between {minimum} and {maximum}. "
        f"Got {result.score}."
    )
