import json

from database import (
    get_conn
)


def get_result(
    evaluation_id: int,
    user_id: int,
):

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

            print(
                "LOOKUP",
                evaluation_id,
                user_id,
            )

            print(
                "ROW",
                row,
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

    return {

        "evaluation":
            evaluation,

        "listing":
            listing,

        "reasons":
            reasons,

        "actions":
            actions,
    }

def load_listing(
    evaluation,
):
    payload = evaluation.get(
        "listing_json"
    )

    if not payload:
        return {}

    if isinstance(
        payload,
        dict,
    ):
        return payload

    return json.loads(
        payload
    )


def load_reasons(
    evaluation,
):
    payload = evaluation.get(
        "reasons_json"
    )

    if not payload:
        return []

    if isinstance(
        payload,
        list,
    ):
        return payload

    return json.loads(
        payload
    )


def load_actions(
    evaluation,
):
    payload = evaluation.get(
        "actions_json"
    )

    if not payload:
        return []

    if isinstance(
        payload,
        list,
    ):
        return payload

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
