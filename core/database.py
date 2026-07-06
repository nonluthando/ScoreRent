import psycopg
from psycopg.rows import dict_row

from core.config import DATABASE_URL


def get_conn():
    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=5,
    )


def init_db():
    conn = get_conn()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    renter_type TEXT NOT NULL,
                    monthly_income INTEGER NOT NULL,
                    documents_json JSONB NOT NULL,
                    is_bursary_student BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluations (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    profile_id INTEGER REFERENCES profiles(id),
                    listing_name TEXT,
                    listing_json JSONB NOT NULL,
                    score INTEGER NOT NULL,
                    verdict TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    reasons_json JSONB NOT NULL,
                    actions_json JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
                """
            )

            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id)"
            )

            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_evaluations_user_id ON evaluations(user_id)"
            )

        conn.commit()

    finally:
        conn.close()
