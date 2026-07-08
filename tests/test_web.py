import json

from routers.web import load_json_field, profile_to_defaults


def test_load_json_field_none_returns_fallback():
    assert load_json_field(None, []) == []


def test_load_json_field_parses_json_string():
    assert load_json_field('["bank_statement", "payslip"]') == [
        "bank_statement",
        "payslip",
    ]
def test_load_json_field_returns_existing_dict_or_list():
    assert load_json_field({"a": 1}) == {"a": 1}
    assert load_json_field(["x"]) == ["x"]


def test_profile_to_defaults_without_profile():
    defaults = profile_to_defaults(None)

    assert defaults["renter_type"] == "worker"
    assert defaults["monthly_income"] == 0
    assert defaults["submitted_documents"] == []
    assert defaults["is_bursary_student"] is False


def test_profile_to_defaults_with_profile():
    profile = {
        "renter_type": "student",
        "monthly_income": 5000,
        "documents_json": json.dumps(["bank_statement", "bursary_letter"]),
        "is_bursary_student": True,
    }

    defaults = profile_to_defaults(profile)

    assert defaults["renter_type"] == "student"
    assert defaults["monthly_income"] == 5000
    assert defaults["submitted_documents"] == [
        "bank_statement",
        "bursary_letter",
    ]
    assert defaults["is_bursary_student"] is True


def test_home_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200


def test_signup_page_loads(client):
    response = client.get("/signup")

    assert response.status_code == 200


def test_login_page_loads(client):
    response = client.get("/login")

    assert response.status_code == 200


def test_dashboard_redirects_when_not_logged_in(client):
    response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_profile_redirects_when_not_logged_in(client):
    response = client.get("/profile", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_results_redirects_when_not_logged_in(client):
    response = client.get("/results/1", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_compare_redirects_when_not_logged_in(client):
    response = client.get("/compare", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_history_redirects_when_not_logged_in(client):
    response = client.get("/history", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_logout_redirects_home(client):
    response = client.get("/logout", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_learn_page_loads(client):
    response = client.get("/learn")

    assert response.status_code == 200


def test_learn_affordability_page_loads(client):
    response = client.get("/learn/rent-affordability")

    assert response.status_code == 200


def test_learn_documents_page_loads(client):
    response = client.get("/learn/documents-landlords-ask-for")

    assert response.status_code == 200


def test_learn_improve_application_page_loads(client):
    response = client.get("/learn/improve-application")

    assert response.status_code == 200


def test_learn_red_flags_page_loads(client):
    response = client.get("/learn/rental-red-flags")

    assert response.status_code == 200
