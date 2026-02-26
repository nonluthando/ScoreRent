import os
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer, BadSignature
from passlib.context import CryptContext
from fastapi import Request
from database import get_conn


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable not set")

serializer = URLSafeTimedSerializer(SECRET_KEY)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------------------------
# Password utilities
# ------------------------------------------------------------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


# ------------------------------------------------------------------
# User persistence
# ------------------------------------------------------------------

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
        user = conn.execute(
            "SELECT * FROM users WHERE email = %s",
            (email.lower().strip(),),
        ).fetchone()
        return user
    finally:
        conn.close()


def get_user_by_id(user_id: int):
    conn = get_conn()
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
        return user
    finally:
        conn.close()


# ------------------------------------------------------------------
# Session handling
# ------------------------------------------------------------------

def make_session_token(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})


def read_session_token(token: str, max_age_seconds: int = 60 * 60 * 24 * 7):
    try:
        return serializer.loads(token, max_age=max_age_seconds)
    except BadSignature:
        return None


def get_current_user(request: Request):
    token = request.cookies.get("session")
    if not token:
        return None

    data = read_session_token(token)
    if not data:
        return None

    user_id = data.get("user_id")
    if not user_id:
        return None

    return get_user_by_id(int(user_id))
