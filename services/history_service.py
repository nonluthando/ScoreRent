from typing import List, Optional

from database.connection import get_conn


def get_history(
    user_id: int,
):
    """
    Retrieve full evaluation history
    for a user.

    Ordered newest first.

    Args:
        user_id:
            Authenticated user.

    Returns:
        List of evaluations.
    """

    conn = get_conn()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT

                    id,

                    listing_name,

                    score,

                    verdict,

                    confidence,

                    created_at

                FROM evaluations

                WHERE user_id=%s

                ORDER BY created_at DESC
                """,
                (
                    user_id,
                ),
            )

            rows = cur.fetchall()

        return rows

    finally:

        conn.close()


def get_history_paginated(
    user_id: int,

    limit: int = 10,

    offset: int = 0,

    verdict: Optional[
        str
    ] = None,
):
    """
    Retrieve paginated history.

    Supports:

    - pagination
    - verdict filtering
    """

    conn = get_conn()

    try:

        with conn.cursor() as cur:

            query = """
                FROM evaluations

                WHERE user_id=%s
            """

            params = [
                user_id
            ]

            if verdict:

                query += """
                    AND verdict=%s
                """

                params.append(
                    verdict
                )

            cur.execute(
                f"""
                SELECT COUNT(*)

                {query}
                """,
                params,
            )

            total = (
                cur.fetchone()[
                    "count"
                ]
            )

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

            rows = (
                cur.fetchall()
            )

        return {

            "total":
                total,

            "limit":
                limit,

            "offset":
                offset,

            "history":
                rows,
        }

    finally:

        conn.close()


def has_history(
    user_id: int,
):
    """
    Check whether user has
    saved evaluations.
    """

    conn = get_conn()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT EXISTS(

                    SELECT 1

                    FROM evaluations

                    WHERE user_id=%s
                )
                """,
                (
                    user_id,
                ),
            )

            exists = (
                cur.fetchone()[
                    "exists"
                ]
            )

        return exists

    finally:

        conn.close()
