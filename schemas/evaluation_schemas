from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EvaluationSummary(BaseModel):
    """
    Lightweight representation of an evaluation.

    Used when returning evaluation history,
    pagination results, and list views.
    """

    id: int = Field(
        description="Unique evaluation identifier"
    )

    listing_name: Optional[str] = Field(
        default=None,
        description="Human-readable listing name"
    )

    score: int = Field(
        ge=0,
        le=100,
        description="Evaluation score"
    )

    verdict: str = Field(
        description=(
            "Application outcome category"
        )
    )

    confidence: str = Field(
        description=(
            "Confidence label for score"
        )
    )

    created_at: str = Field(
        description=(
            "Timestamp when evaluation was created"
        )
    )


class EvaluationDetail(BaseModel):
    """
    Full evaluation payload.

    Returned when viewing a specific
    saved evaluation.
    """

    id: int = Field(
        description="Evaluation identifier"
    )

    listing: Dict[str, Any] = Field(
        description=(
            "Serialized listing information"
        )
    )

    score: int = Field(
        ge=0,
        le=100,
        description="Final evaluation score"
    )

    verdict: str = Field(
        description=(
            "Recommendation outcome"
        )
    )

    confidence: str = Field(
        description=(
            "Confidence level"
        )
    )

    created_at: str = Field(
        description=(
            "Creation timestamp"
        )
    )


class EvaluationListResponse(BaseModel):
    """
    Paginated response model for
    evaluation history.
    """

    total: int = Field(
        description=(
            "Total evaluations available"
        )
    )

    limit: int = Field(
        description=(
            "Requested page size"
        )
    )

    offset: int = Field(
        description=(
            "Pagination offset"
        )
    )

    evaluations: List[
        EvaluationSummary
    ] = Field(
        description=(
            "Evaluation history records"
        )
    )


class EvaluationFilter(BaseModel):
    """
    Optional filtering model used
    when querying evaluations.
    """

    verdict: Optional[str] = Field(
        default=None,
        description=(
            "Filter evaluations by verdict"
        )
    )


class EvaluationPagination(BaseModel):
    """
    Pagination configuration model.
    """

    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description=(
            "Maximum rows returned"
        )
    )

    offset: int = Field(
        default=0,
        ge=0,
        description=(
            "Rows skipped before retrieval"
        )
    )
