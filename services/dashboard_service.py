from database.connection import get_conn


def get_latest_evaluation(
    user_id: int,
):
    """
    Retrieve the most recent
    saved evaluation for a user.

    Args:
        user_id:
            Authenticated user ID.

    Returns:
        evaluation row
        or None
    """

    conn = get_conn()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT *

                FROM evaluations

                WHERE user_id=%s

                ORDER BY created_at DESC

                LIMIT 1
                """,
                (
                    user_id,
                ),
            )

            evaluation = (
                cur.fetchone()
            )

        return evaluation

    finally:

        conn.close()


def build_dashboard(
    user_id: int,
):
    """
    Build dashboard payload.

    Returns:

    {
        last_eval
    }
    """

    latest = (
        get_latest_evaluation(
            user_id
        )
    )

    return {

        "last_eval":
            latest
    }


def has_evaluations(
    user_id: int,
):
    """
    Check whether user has
    evaluation history.
    """

    conn = get_conn()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT COUNT(*)

                FROM evaluations

                WHERE user_id=%s
                """,
                (
                    user_id,
                ),
            )

            count = (
                cur.fetchone()[
                    "count"
                ]
            )

        return count > 0

    finally:

        conn.close()
