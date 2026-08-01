import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://scorerent:scorerent@localhost:5432/scorerent",
)


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

            # Users
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

            # Profiles
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

            # Evaluations
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

            # Saved listings
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS listings (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    location TEXT,
                    monthly_rent INTEGER NOT NULL,
                    deposit INTEGER NOT NULL DEFAULT 0,
                    application_fee INTEGER NOT NULL DEFAULT 0,
                    upfront_cost INTEGER NOT NULL,
                    area_demand TEXT NOT NULL DEFAULT 'MEDIUM',
                    required_documents_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    amenities_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    pros_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    cons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    source_url TEXT,
                    notes TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
                """
            )

            # Saved destinations for commute comparisons
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_destinations (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    label TEXT NOT NULL,
                    address TEXT NOT NULL,
                    latitude DOUBLE PRECISION NOT NULL,
                    longitude DOUBLE PRECISION NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )

            # Cached routes between saved listings and destinations
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS listing_commutes (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
                    destination_id INTEGER NOT NULL REFERENCES saved_destinations(id) ON DELETE CASCADE,
                    travel_mode TEXT NOT NULL,
                    distance_metres INTEGER NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL,
                    UNIQUE (listing_id, destination_id, travel_mode)
                )
                """
            )

            # Safe additive migration for existing listing tables
            cur.execute(
                "ALTER TABLE listings ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION"
            )
            cur.execute(
                "ALTER TABLE listings ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION"
            )
            cur.execute(
                "ALTER TABLE listings ADD COLUMN IF NOT EXISTS geocoded_address TEXT"
            )

            # Indexes for performance
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id)"
            )

            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_evaluations_user_id ON evaluations(user_id)"
            )

            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_listings_user_id ON listings(user_id)"
            )

            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_saved_destinations_user_id ON saved_destinations(user_id)"
            )

            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_listing_commutes_listing_id ON listing_commutes(listing_id)"
            )

        conn.commit()
    finally:
        conn.close()
