# app/core/security.py

from itsdangerous import URLSafeTimedSerializer, BadSignature
from passlib.context import CryptContext

from app.core.config import SECRET_KEY


serializer = URLSafeTimedSerializer(SECRET_KEY)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def make_session_token(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})


def read_session_token(token: str, max_age_seconds: int = 60 * 60 * 24 * 7):
    try:
        return serializer.loads(token, max_age=max_age_seconds)
    except BadSignature:
        return None
