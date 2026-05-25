import json
from datetime import datetime
from typing import Optional

from database.connection import get_conn

from schemas.evaluation_schema import (
    EvaluationSummary,
    EvaluationDetail,
)


# ---------------------------------------------------------
# Evaluation retrieval
# ---------------------------------------------------------

def get_user_evaluations(
    user_id: int,
    limit: int,
    offset: int,
    verdict: Optional[str] = None,
):
    """
    Retrieve paginated evaluation
    history.

    Supports:

    - pagination
    - verdict filtering
    """

    conn = get_conn()

    try:

        with conn.cursor() as cur:

            query, params = build_filters(
                user_id=user_id,
                verdict=verdict,
            )

            cur.execute(
                f"""
                SELECT COUNT(*)

                {query}
                """,
                params,
            )

            total = cur.fetchone()["count"]

            cur.execute(
                f"""
                SELECT

                    id,

                    listing_name,

                    score,

                    verdict,

                    confidence,

                    created_at

                {query}

                ORDER BY created_at DESC

                LIMIT %s
                OFFSET %s
                """,
                (
                    *params,
                    limit,
                    offset,
                ),
            )

            rows = cur.fetchall()

        summaries = [

            map_summary(
                row
            )

            for row in rows
        ]

        return {

            "total":
                total,

            "limit":
                limit,

            "offset":
                offset,

            "evaluations":
                summaries,
        }

    finally:

        conn.close()


def get_single_evaluation(
    evaluation_id: int,
    user_id: int,
):
    """
    Retrieve single evaluation
    owned by user.
    """

    conn = get_conn()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT *

                FROM evaluations

                WHERE

                    id=%s

                AND

                    user_id=%s
                """,
                (
                    evaluation_id,
                    user_id,
                ),
            )

            row = cur.fetchone()

        if not row:
            return None

        return map_detail(
            row
        )

    finally:

        conn.close()


# ---------------------------------------------------------
# Persistence
# ---------------------------------------------------------

def create_listing_payload(
    listing_name: str,

    rent: int,

    deposit: int,

    application_fee: int,

    required_documents,

    area_demand: str,

    guarantor_monthly_income: int,

    breakdown,
):
    """
    Build evaluation payload.
    """

    return {

        "listing_name":
            listing_name.strip(),

        "rent":
            int(rent),

        "deposit":
            int(deposit),

        "application_fee":
            int(
                application_fee
            ),

        "required_documents":
            required_documents,

        "area_demand":
            area_demand,

        "guarantor_monthly_income":
            int(
                guarantor_monthly_income
            ),

        "breakdown":
            breakdown,
    }


def build_guest_result(
    listing,
    result,
    bands,
):
    """
    Guest evaluations are
    returned but not saved.
    """

    return {

        "listing":
            listing,

        "result":
            result,

        "bands":
            bands,

        "guest":
            True,
    }


def save_evaluation(
    user_id: int,

    profile_id: int,

    listing_name: str,

    listing,

    result,
):
    """
    Save evaluation and return ID.
    """

    conn = get_conn()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO evaluations(

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

                VALUES(

                    %s,

                    %s,

                    %s,

                    %s,

                    %s,

                    %s,

                    %s,

                    %s,

                    %s,

                    %s
                )

                RETURNING id
                """,

                (
                    user_id,

                    profile_id,

                    listing_name,

                    json.dumps(
                        listing
                    ),

                    int(
                        result.score
                    ),

                    result.verdict,

                    result.confidence,

                    json.dumps(
                        result.reasons
                    ),

                    json.dumps(
                        result.actions
                    ),

                    datetime.utcnow(
                    ).isoformat(),
                ),
            )

            evaluation_id = (
                cur.fetchone()[
                    "id"
                ]
            )

            conn.commit()

        return evaluation_id

    finally:

        conn.close()


def insert_evaluation(
    user_id,

    profile_id,

    listing_name,

    listing,

    result,
):
    """
    Wrapper for persistence.
    """

    return save_evaluation(

        user_id=
            user_id,

        profile_id=
            profile_id,

        listing_name=
            listing_name,

        listing=
            listing,

        result=
            result,
    )


def default_listing_name(
    listing_name: str,
    rent: int,
):
    """
    Generate fallback name.
    """

    name = (
        listing_name
        .strip()
    )

    if name:
        return name

    return f"Listing (R{rent})"


# ---------------------------------------------------------
# Query helpers
# ---------------------------------------------------------

def build_filters(
    user_id: int,
    verdict: Optional[str],
):
    """
    Build reusable filters.
    """

    query = """
        FROM evaluations

        WHERE user_id=%s
    """

    params = [user_id]

    if verdict:

        query += """
            AND verdict=%s
        """

        params.append(
            verdict
        )

    return (
        query,
        params,
    )


# ---------------------------------------------------------
# Mapping
# ---------------------------------------------------------

def map_summary(
    row,
):
    """
    Map DB row to summary.
    """

    return EvaluationSummary(

        id=row["id"],

        listing_name=
            row[
                "listing_name"
            ],

        score=row["score"],

        verdict=
            row[
                "verdict"
            ],

        confidence=
            row[
                "confidence"
            ],

        created_at=str(
            row[
                "created_at"
            ]
        ),
    )


def map_detail(
    row,
):
    """
    Map DB row to detail.
    """

    return EvaluationDetail(

        id=row["id"],

        listing=json.loads(
            row[
                "listing_json"
            ]
        ),

        score=row["score"],

        verdict=
            row[
                "verdict"
            ],

        confidence=
            row[
                "confidence"
            ],

        created_at=str(
            row[
                "created_at"
            ]
        ),
    )
