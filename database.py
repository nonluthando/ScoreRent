import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://scorerent:scorerent@localhost:5432/scorerent",
)


def get_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=5)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

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
            documents_json TEXT NOT NULL,

            -- ✅ NEW FIELDS (saved student context)
            is_bursary_student BOOLEAN NOT NULL DEFAULT FALSE,
            guarantor_monthly_income INTEGER NOT NULL DEFAULT 0,

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
            listing_json TEXT NOT NULL,
            score INTEGER NOT NULL,
            verdict TEXT NOT NULL,
            confidence TEXT NOT NULL,
            reasons_json TEXT NOT NULL,
            actions_json TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        """
    )

    # ✅ Option 1 migration approach:
    # If table already exists, ensure new columns exist.
    cur.execute(
        """
        ALTER TABLE profiles
        ADD COLUMN IF NOT EXISTS is_bursary_student BOOLEAN NOT NULL DEFAULT FALSE
        """
    )

    cur.execute(
        """
        ALTER TABLE profiles
        ADD COLUMN IF NOT EXISTS guarantor_monthly_income INTEGER NOT NULL DEFAULT 0
        """
    )

    conn.commit()
    cur.close()
    conn.close()
