import sqlite3
from pathlib import Path

DB_PATH = Path("scorerent.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _col_exists(conn, table: str, col: str) -> bool:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(c["name"] == col for c in cols)


def migrate_db(conn):
    """
    Applies migrations safely for existing DBs.
    """
    # ---- profiles migrations ----
    if not _col_exists(conn, "profiles", "documents_json"):
        conn.execute("ALTER TABLE profiles ADD COLUMN documents_json TEXT")
        conn.execute("UPDATE profiles SET documents_json = '[]' WHERE documents_json IS NULL")
        conn.commit()

    # ---- evaluations migrations ----
    if not _col_exists(conn, "evaluations", "listing_name"):
        conn.execute("ALTER TABLE evaluations ADD COLUMN listing_name TEXT")
        conn.commit()


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            renter_type TEXT NOT NULL,
            monthly_income INTEGER NOT NULL,
            documents_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            profile_id INTEGER,
            listing_name TEXT,
            listing_json TEXT NOT NULL,
            score INTEGER NOT NULL,
            verdict TEXT NOT NULL,
            confidence TEXT NOT NULL,
            reasons_json TEXT NOT NULL,
            actions_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(profile_id) REFERENCES profiles(id)
        )
        """
    )

    conn.commit()

    #  apply migrations AFTER base tables exist
    migrate_db(conn)

    conn.close()
