import json

from database import (
    get_conn
)


def get_result(
    evaluation_id: int,

    user_id: int,
):
    """
    Retrieve evaluation result
    owned by a user.

    Ownership validation is
    enforced.

    Args:

        evaluation_id:
            Result identifier

        user_id:
            Current user

    Returns:

        mapped result
        or None
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

            row = (
                cur.fetchone()
            )

        if not row:
            return None

        return map_result(
            row
        )

    finally:

        conn.close()


def map_result(
    evaluation,
):
    """
    Convert database row
    into result payload.
    """

    listing = load_listing(
        evaluation
    )

    reasons = load_reasons(
        evaluation
    )

    actions = load_actions(
        evaluation
    )

    bands = listing.get(
        "budget_bands",
        {}
    )

    return {

        "evaluation":
            evaluation,

        "listing":
            listing,

        "reasons":
            reasons,

        "actions":
            actions,

        "bands":
            bands,
    }


def load_listing(
    evaluation,
):
    """
    Parse listing payload.
    """

    payload = evaluation.get(
        "listing_json"
    )

    if not payload:
        return {}

    return json.loads(
        payload
    )


def load_reasons(
    evaluation,
):
    """
    Parse recommendation
    reasons.
    """

    payload = evaluation.get(
        "reasons_json"
    )

    if not payload:
        return []

    return json.loads(
        payload
    )


def load_actions(
    evaluation,
):
    """
    Parse recommended
    actions.
    """

    payload = evaluation.get(
        "actions_json"
    )

    if not payload:
        return []

    return json.loads(
        payload
    )


def result_exists(
    evaluation_id: int,

    user_id: int,
):
    """
    Check result ownership.
    """

    conn = get_conn()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT EXISTS(

                    SELECT 1

                    FROM evaluations

                    WHERE

                        id=%s

                    AND

                        user_id=%s
                )
                """,
                (
                    evaluation_id,

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
