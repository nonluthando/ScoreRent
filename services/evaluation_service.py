from typing import Optional
import json

from database.connection import get_conn
from schemas.evaluation_schema import (
    EvaluationDetail,
    EvaluationSummary,
)


def get_user_evaluations(
    user_id: int,
    limit: int,
    offset: int,
    verdict: Optional[str] = None,
):
    """
    Retrieve paginated evaluation history
    for a specific user.

    Supports optional filtering by verdict.

    Args:
        user_id:
            Authenticated user identifier.

        limit:
            Maximum number of records.

        offset:
            Pagination offset.

        verdict:
            Optional verdict filter.

    Returns:
        dict containing:

        {
            total,
            limit,
            offset,
            evaluations
        }
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
            "total": total,
            "limit": limit,
            "offset": offset,
            "evaluations": summaries,
        }

    finally:
        conn.close()


def get_single_evaluation(
    evaluation_id: int,
    user_id: int,
):
    """
    Retrieve a single evaluation
    belonging to a user.

    Ownership validation is enforced.

    Args:
        evaluation_id:
            Evaluation identifier.

        user_id:
            Current authenticated user.

    Returns:
        EvaluationDetail
        or None.
    """

    conn = get_conn()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT *

                FROM evaluations

                WHERE
                    id = %s
                AND
                    user_id = %s
                """,
                (
                    evaluation_id,
                    user_id,
                ),
            )

            result = cur.fetchone()

        if not result:
            return None

        return map_detail(
            result
        )

    finally:
        conn.close()


def build_filters(
    user_id: int,
    verdict: Optional[str],
):
    """
    Build reusable query filters.

    Args:
        user_id:
            User ownership filter.

        verdict:
            Optional verdict value.

    Returns:
        tuple:
            (
                sql,
                params
            )
    """

    query = """
        FROM evaluations

        WHERE user_id = %s
    """

    params = [user_id]

    if verdict:

        query += """
            AND verdict = %s
        """

        params.append(
            verdict
        )

    return query, params


def map_summary(
    row,
):
    """
    Convert database row
    into EvaluationSummary.
    """

    return EvaluationSummary(
        id=row["id"],
        listing_name=row[
            "listing_name"
        ],
        score=row["score"],
        verdict=row[
            "verdict"
        ],
        confidence=row[
            "confidence"
        ],
        created_at=str(
            row["created_at"]
        ),
    )


def map_detail(
    row,
):
    """
    Convert database row
    into EvaluationDetail.
    """

    return EvaluationDetail(
        id=row["id"],

        listing=json.loads(
            row[
                "listing_json"
            ]
        ),

        score=row["score"],

        verdict=row[
            "verdict"
        ],

        confidence=row[
            "confidence"
        ],

        created_at=str(
            row["created_at"]
        ),
    )
