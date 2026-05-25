import json

from database.connection import get_conn


def get_latest_profile(
    user_id: int,
):
    """
    Retrieve most recent renter
    profile for a user.

    Returns:
        profile dict
        or None
    """

    conn = get_conn()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT *

                FROM profiles

                WHERE user_id=%s

                ORDER BY created_at DESC

                LIMIT 1
                """,
                (
                    user_id,
                ),
            )

            profile = cur.fetchone()

        return profile

    finally:

        conn.close()


def normalize_profile(
    profile,
):
    """
    Convert profile row into
    template-friendly structure.
    """

    if not profile:

        return {

            "docs_selected": [],

            "renter_type":
                "worker",

            "monthly_income":
                0,

            "is_bursary_student":
                False,
        }

    return {

        "docs_selected":

            json.loads(
                profile[
                    "documents_json"
                ]
            ),

        "renter_type":

            profile[
                "renter_type"
            ],

        "monthly_income":

            profile[
                "monthly_income"
            ],

        "is_bursary_student":

            bool(
                profile.get(
                    "is_bursary_student",
                    False,
                )
            ),
    }
