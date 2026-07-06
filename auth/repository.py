# app/auth/repository.py

from datetime import datetime

from app.core.database import get_conn
from app.core.security import hash_password


def create_user(email: str, password: str) -> int:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (email, password_hash, created_at)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (
                    email.lower().strip(),
                    hash_password(password),
                    datetime.utcnow().isoformat(),
                ),
            )
            user_id = cur.fetchone()["id"]

        conn.commit()
        return user_id

    finally:
        conn.close()


def get_user_by_email(email: str):
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = %s",
            (email.lower().strip(),),
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id: int):
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
