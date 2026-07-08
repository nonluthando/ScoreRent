import json
from datetime import datetime, timedelta

import pytest

import routers.api as api_router


def test_api_load_json_field_none_returns_fallback():
    assert api_router.load_json_field(None, []) == []


def test_api_load_json_field_parses_json_string():
    assert api_router.load_json_field('{"rent": 8500}') == {"rent": 8500}


def test_api_evaluations_requires_authentication(client):
    response = client.get("/api/evaluations")

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


def test_api_evaluation_detail_requires_authentication(client):
    response = client.get("/api/evaluations/1")

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


def test_list_evaluations_returns_authenticated_user_evaluations(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        api_router,
        "get_current_user",
        lambda request: {"id": 1, "email": "test@example.com"},
    )

    created_at = datetime.utcnow().isoformat()

    conn = api_router.get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO evaluations (
                user_id,
                profile_id,
                listing_name,
                listing_json,
                score,
                verdict,
                confidence,
                reasons_json,
                actions_json,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                1,
                None,
                "Test Listing",
                json.dumps({"rent": 8500}),
                78,
                "BORDERLINE",
                "HIGH",
                json.dumps(["Affordability risk"]),
                json.dumps(["Add documents"]),
                created_at,
            ),
        )
        conn.commit()
    conn.close()

    response = client.get("/api/evaluations")

    assert response.status_code == 200

    body = response.json()
    assert body["total"] >= 1
    assert body["limit"] == 10
    assert body["offset"] == 0
    assert body["evaluations"][0]["listing_name"] == "Test Listing"
    assert body["evaluations"][0]["score"] == 78


def test_list_evaluations_filters_by_verdict(client, monkeypatch):
    monkeypatch.setattr(
        api_router,
        "get_current_user",
        lambda request: {"id": 1, "email": "test@example.com"},
    )

    conn = api_router.get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO evaluations (
                user_id,
                profile_id,
                listing_name,
                listing_json,
                score,
                verdict,
                confidence,
                reasons_json,
                actions_json,
                created_at
            )
            VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s),
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                1,
                None,
                "Worth Listing",
                json.dumps({"rent": 7000}),
                88,
                "WORTH_APPLYING",
                "HIGH",
                json.dumps([]),
                json.dumps([]),
                datetime.utcnow().isoformat(),
                1,
                None,
                "Risky Listing",
                json.dumps({"rent": 15000}),
                40,
                "NOT_WORTH_IT",
                "HIGH",
                json.dumps([]),
                json.dumps([]),
                (datetime.utcnow() + timedelta(seconds=1)).isoformat(),
            ),
        )
        conn.commit()
    conn.close()

    response = client.get("/api/evaluations?verdict=NOT_WORTH_IT")

    assert response.status_code == 200

    body = response.json()
    assert body["total"] >= 1
    assert all(
        evaluation["verdict"] == "NOT_WORTH_IT"
        for evaluation in body["evaluations"]
    )


def test_get_evaluation_returns_detail_for_owner(client, monkeypatch):
    monkeypatch.setattr(
        api_router,
        "get_current_user",
        lambda request: {"id": 1, "email": "test@example.com"},
    )

    conn = api_router.get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO evaluations (
                user_id,
                profile_id,
                listing_name,
                listing_json,
                score,
                verdict,
                confidence,
                reasons_json,
                actions_json,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                1,
                None,
                "Detail Listing",
                json.dumps({"rent": 9000, "area_demand": "HIGH"}),
                65,
                "BORDERLINE",
                "MEDIUM",
                json.dumps(["High demand area"]),
                json.dumps(["Prepare documents"]),
                datetime.utcnow().isoformat(),
            ),
        )

        evaluation_id = cur.fetchone()["id"]
        conn.commit()
    conn.close()

    response = client.get(f"/api/evaluations/{evaluation_id}")

    assert response.status_code == 200

    body = response.json()
    assert body["id"] == evaluation_id
    assert body["listing"]["rent"] == 9000
    assert body["score"] == 65
    assert body["verdict"] == "BORDERLINE"


def test_get_evaluation_returns_404_for_missing_or_other_user(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        api_router,
        "get_current_user",
        lambda request: {"id": 1, "email": "test@example.com"},
    )

    response = client.get("/api/evaluations/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Not found"
