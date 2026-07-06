from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class EvaluationSummary(BaseModel):
    id: int
    listing_name: Optional[str]

    score: int

    verdict: str

    confidence: str

    created_at: str


class EvaluationDetail(BaseModel):
    id: int

    listing: Dict[str, Any]

    score: int

    verdict: str

    confidence: str

    created_at: str


class EvaluationListResponse(BaseModel):
    total: int

    limit: int

    offset: int

    evaluations: List[EvaluationSummary]
