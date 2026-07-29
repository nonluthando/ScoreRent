import os
from urllib.parse import urlparse

import pytest

# Ensure imports never default to the development database during test collection.
os.environ.setdefault(
    "DATABASE_URL",
    os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://scorerent:scorerent@localhost:5432/scorerent_test_unconfigured",
    ),
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")


def _configured_test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run database-backed tests.")

    database_name = urlparse(database_url).path.lstrip("/").lower()
    if "test" not in database_name:
        raise RuntimeError(
            "Refusing destructive tests: the TEST_DATABASE_URL database name must contain 'test'."
        )

    return database_url


@pytest.fixture(scope="session")
def client():
    database_url = _configured_test_database_url()
    os.environ["DATABASE_URL"] = database_url

    # Imports are delayed until the safe test URL is verified.
    import database
    database.DATABASE_URL = database_url
    from fastapi.testclient import TestClient
    from main import app

    database.init_db()
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_database(request):
    if "client" not in request.fixturenames:
        yield
        return

    database_url = _configured_test_database_url()
    import database
    database.DATABASE_URL = database_url

    conn = database.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM evaluations")
            cur.execute("DELETE FROM profiles")
            cur.execute("DELETE FROM users")
        conn.commit()
    finally:
        conn.close()

    yield


@pytest.fixture
def worker_payload():
    return {
        "renter_type": "worker",
        "monthly_income": 30000,
        "submitted_documents": ["bank statement", "payslip"],
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
        "submitted_documents": ["nsfas award letter"],
        "monthly_rent": 7000,
        "security_deposit": 7000,
        "application_fee": 0,
        "required_documents": [],
        "area_demand": "MEDIUM",
        "is_bursary_student": True,
    }


def assert_reason_contains(result, text):
    assert any(text.lower() in reason.lower() for reason in result.reasons)


def assert_action_contains(result, text):
    assert any(text.lower() in action.lower() for action in result.actions)


def assert_score_range(result, minimum, maximum):
    assert minimum <= result.score <= maximum
