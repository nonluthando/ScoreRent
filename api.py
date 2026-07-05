from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import json

from auth import get_current_user
from database import get_conn


router = APIRouter(prefix="/api", tags=["api"])


class EvaluationSummary(BaseModel):
    id: int
    listing_name: Optional[str]
    score: int
    verdict: str
    confidence: str
    created_at: str


class EvaluationDetail(BaseModel):
    id: int
    listing: dict
    score: int
    verdict: str
    confidence: str
    created_at: str


class EvaluationListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    evaluations: List[EvaluationSummary]


@router.get("/evaluations", response_model=EvaluationListResponse)
def list_evaluations(
    request: Request,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    verdict: Optional[str] = None,
):
    user = get_current_user(request)

    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_conn()

    try:
        with conn.cursor() as cur:
            base_query = """
                FROM evaluations
                WHERE user_id = %s
            """
            params = [user["id"]]

            if verdict:
                base_query += " AND verdict = %s"
                params.append(verdict)

            cur.execute(f"SELECT COUNT(*) {base_query}", params)
            total = cur.fetchone()["count"]

            cur.execute(
                f"""
                SELECT id, listing_name, score, verdict, confidence, created_at
                {base_query}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (*params, limit, offset),
            )

            rows = cur.fetchall()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "evaluations": rows,
        }

    finally:
        conn.close()


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationDetail)
def get_evaluation(request: Request, evaluation_id: int):
    user = get_current_user(request)

    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_conn()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM evaluations
                WHERE id = %s AND user_id = %s
                """,
                (evaluation_id, user["id"]),
            )

            evaluation = cur.fetchone()

        if not evaluation:
            raise HTTPException(status_code=404, detail="Not found")

        listing_json = evaluation["listing_json"]

        if isinstance(listing_json, dict):
            listing = listing_json
        else:
            listing = json.loads(listing_json)

        return {
            "id": evaluation["id"],
            "listing": listing,
            "score": evaluation["score"],
            "verdict": evaluation["verdict"],
            "confidence": evaluation["confidence"],
            "created_at": evaluation["created_at"],
        }

    finally:
        conn.close()
