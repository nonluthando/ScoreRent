from fastapi import APIRouter, Request, HTTPException
from auth import get_current_user
from database import get_conn
import from fastapi import APIRouter, Request, HTTPException
from auth import get_current_user
from database import get_conn
import json

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/evaluations")
def list_evaluations(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, listing_name, score, verdict, confidence, created_at FROM evaluations WHERE user_id = %s ORDER BY created_at DESC",
        (user["id"],),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return {"evaluations": rows}


@router.get("/evaluations/{evaluation_id}")
def get_evaluation(request: Request, evaluation_id: int):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM evaluations WHERE id = %s AND user_id = %s",
        (evaluation_id, user["id"]),
    )
    ev = cur.fetchone()
    cur.close()
    conn.close()

    if not ev:
        raise HTTPException(status_code=404, detail="Not found")

    return {
        "id": ev["id"],
        "listing": json.loads(ev["listing_json"]),
        "score": ev["score"],
        "verdict": ev["verdict"],
        "confidence": ev["confidence"],
        "created_at": ev["created_at"],
    }
router = APIRouter(prefix="/api", tags=["api"])


@router.get("/evaluations")
def list_evaluations(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, listing_name, score, verdict, confidence, created_at FROM evaluations WHERE user_id = %s ORDER BY created_at DESC",
        (user["id"],),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return {"evaluations": rows}


@router.get("/evaluations/{evaluation_id}")
def get_evaluation(request: Request, evaluation_id: int):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM evaluations WHERE id = %s AND user_id = %s",
        (evaluation_id, user["id"]),
    )
    ev = cur.fetchone()
    cur.close()
    conn.close()

    if not ev:
        raise HTTPException(status_code=404, detail="Not found")

    return {
        "id": ev["id"],
        "listing": json.loads(ev["listing_json"]),
        "score": ev["score"],
        "verdict": ev["verdict"],
        "confidence": ev["confidence"],
        "created_at": ev["created_at"],
    }
