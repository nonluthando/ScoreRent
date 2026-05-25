from fastapi import APIRouter, Request, HTTPException, Query
from typing import Optional

from auth import get_current_user

from schemas.evaluation_schema import (
    EvaluationListResponse,
    EvaluationDetail,
)

from services.evaluation_service import (
    get_user_evaluations,
    get_single_evaluation,
)

router = APIRouter(
    prefix="/api",
    tags=["evaluations"]
)


@router.get(
    "/evaluations",
    response_model=EvaluationListResponse,
)
def list_evaluations(
    request: Request,
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    verdict: Optional[str] = None,
):
    """
    Retrieve evaluation history for the authenticated user.

    Returns a paginated collection of previously saved rental
    evaluations owned by the current user.

    Supports optional filtering by evaluation verdict and
    pagination controls.

    Args:
        request:
            Incoming request object containing user session data.

        limit:
            Maximum number of evaluations returned.

            Constraints:
            - minimum = 1
            - maximum = 100

        offset:
            Number of records skipped before retrieval.

        verdict:
            Optional filter for evaluation outcome.

            Examples:
            - "Worth applying"
            - "Borderline"
            - "Not worth it"

    Returns:
        EvaluationListResponse:

        {
            total,
            limit,
            offset,
            evaluations
        }

    Raises:
        HTTPException:
            401 Unauthorized if no authenticated user exists.
    """

    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )

    return get_user_evaluations(
        user_id=user["id"],
        limit=limit,
        offset=offset,
        verdict=verdict,
    )


@router.get(
    "/evaluations/{evaluation_id}",
    response_model=EvaluationDetail,
)
def get_evaluation(
    request: Request,
    evaluation_id: int,
):
    """
    Retrieve a single evaluation by ID.

    Returns detailed evaluation information including
    listing data, confidence score, verdict,
    and metadata.

    Ownership validation is enforced to ensure users
    may only access their own evaluations.

    Args:
        request:
            Incoming request object containing user
            authentication context.

        evaluation_id:
            Unique identifier of the evaluation.

    Returns:
        EvaluationDetail:

        {
            id,
            listing,
            score,
            verdict,
            confidence,
            created_at
        }

    Raises:
        HTTPException:
            401 Unauthorized
                User session not found.

            404 Not Found
                Evaluation does not exist or
                does not belong to current user.
    """

    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )

    evaluation = get_single_evaluation(
        evaluation_id=evaluation_id,
        user_id=user["id"],
    )

    if not evaluation:
        raise HTTPException(
            status_code=404,
            detail="Evaluation not found",
        )

    return evaluation
