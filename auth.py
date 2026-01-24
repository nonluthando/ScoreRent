from datetime import datetime
from itsdangerous import URLSafeTimedSerializer, BadSignature
from passlib.context import CryptContext
from fastapi import Request
from database import get_conn

SECRET_KEY = "CHANGE_ME__SCORERENT_SECRET"
serializer = URLSafeTimedSerializer(SECRET_KEY)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_user(email: str, password: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (email, password_hash, created_at)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (email.lower().strip(), hash_password(password), datetime.utcnow().isoformat()),
    )
    user_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return user_id


def get_user_by_email(email: str):
    conn = get_conn()
    user = conn.execute(
        "SELECT * FROM users WHERE email = %s",
        (email.lower().strip(),),
    ).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id: int):
    conn = get_conn()
    user = conn.execute(
        "SELECT * FROM users WHERE id = %s",
        (user_id,),
    ).fetchone()
    conn.close()
    return user


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
