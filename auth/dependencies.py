# app/auth/dependencies.py

from fastapi import Request

from app.auth.repository import get_user_by_id
from app.core.security import read_session_token


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
