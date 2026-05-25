from typing import List, Tuple

from engine.models import EvaluationResult

from engine.config import (
    APP_MARKET,
    RENTER_TYPES,
    DEMAND_LEVELS,
)

from engine.breakdown import (
    push_breakdown,
)

from engine.helpers import (
    money,
    dedupe_keep_order,
)

from engine.affordability import (
    evaluate_affordability,
)

from engine.student_rules import (
    evaluate_student_support,
)

from engine.document_rules import (
    evaluate_required_documents,
)

from engine.demand import (
    evaluate_market_demand,
)

from engine.verdict import (
    determine_verdict,
)

from engine.budget import (
    suggested_budget_bands,
)


def evaluate(
    renter_type: str,
    monthly_income: int,
    renter_docs: List[str],

    rent: int,
    deposit: int,
    application_fee: int,

    required_documents: List[str],

    area_demand: str,

    guarantor_monthly_income: int = 0,

    is_bursary_student: bool = False,
) -> Tuple[
    EvaluationResult,
    dict,
]:
    """
    Main decision engine.

    Coordinates:

    - student rules
    - affordability
    - documents
    - demand
    - verdict generation

    Returns:

        (
            EvaluationResult,
            budget_bands
        )
    """

    monthly_income = money(
        monthly_income
    )

    rent = money(
        rent
    )

    deposit = money(
        deposit
    )

    application_fee = money(
        application_fee
    )

    guarantor_monthly_income = money(
        guarantor_monthly_income
    )

    renter_type = (
        renter_type
        .strip()
        .lower()
    )

    if renter_type not in RENTER_TYPES:
        renter_type = "worker"

    area_demand = (
        area_demand
        .strip()
        .upper()
    )

    if area_demand not in DEMAND_LEVELS:
        area_demand = "MEDIUM"

    renter_docs_set = set(
        d.strip().lower()
        for d in renter_docs
    )

    required_docs_set = set(
        d.strip().lower()
        for d in required_documents
    )

    score = 100

    reasons = []

    actions = []

    breakdown = []

    push_breakdown(
        breakdown,
        "Base score",
        0,
        0,
        score,
        (
            f"Calibrated for "
            f"{APP_MARKET}"
        ),
    )

    effective_income = (
        monthly_income
    )

    affordability_skip = False

    is_student = (
        renter_type
        == "student"
    )

    # -------------------------
    # Student handling
    # -------------------------

    if is_student:

        (
            score,
            effective_income,
            affordability_skip,
        ) = evaluate_student_support(

            score=score,

            breakdown=breakdown,

            reasons=reasons,

            actions=actions,

            renter_docs=renter_docs_set,

            monthly_income=monthly_income,

            rent=rent,

            guarantor_monthly_income=(
                guarantor_monthly_income
            ),

            is_bursary_student=(
                is_bursary_student
            ),
        )

    # -------------------------
    # Affordability
    # -------------------------

    if not affordability_skip:

        score = (
            evaluate_affordability(

                score=score,

                breakdown=breakdown,

                reasons=reasons,

                monthly_income=(
                    effective_income
                ),

                rent=rent,
            )
        )

    # -------------------------
    # Documents
    # -------------------------

    score = (
        evaluate_required_documents(

            score=score,

            breakdown=breakdown,

            reasons=reasons,

            actions=actions,

            renter_docs=(
                renter_docs_set
            ),

            required_docs=(
                required_docs_set
            ),
        )
    )

    # -------------------------
    # Market demand
    # -------------------------

    score = (
        evaluate_market_demand(

            score=score,

            breakdown=breakdown,

            reasons=reasons,

            area_demand=(
                area_demand
            ),
        )
    )

    # -------------------------
    # Final verdict
    # -------------------------

    (
        score,
        verdict,
        confidence,
    ) = determine_verdict(

        score=score,

        breakdown=breakdown,
    )

    reasons = dedupe_keep_order(
        reasons
    )[:5]

    actions = dedupe_keep_order(
        actions
    )[:4]

    result = EvaluationResult(

        score=score,

        verdict=verdict,

        confidence=confidence,

        reasons=reasons,

        actions=actions,

        breakdown=breakdown,
    )

    return (
        result,
        suggested_budget_bands(
            effective_income
        ),
    )
