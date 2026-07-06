# app/auth/service.py

from app.auth.repository import create_user, get_user_by_email
from app.core.security import verify_password


def register_user(email: str, password: str) -> int:
    existing_user = get_user_by_email(email)

    if existing_user:
        raise ValueError("User already exists")

    return create_user(email=email, password=password)


def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)

    if not user:
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    return user
