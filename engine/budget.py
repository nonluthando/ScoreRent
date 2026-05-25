from typing import List

from engine.breakdown import (
    apply_score_change,
)

from engine.helpers import money


def evaluate_upfront_cost_risk(
    score: int,

    breakdown: List,

    reasons: List[str],

    actions: List[str],

    rent: int,

    deposit: int,

    application_fee: int,

    monthly_income: int,
):
    """
    Evaluate affordability pressure
    caused by upfront costs.

    Uses:

    rent +
    deposit +
    application fee

    Returns:
        updated_score
    """

    rent = money(
        rent
    )

    deposit = money(
        deposit
    )

    application_fee = money(
        application_fee
    )

    monthly_income = money(
        monthly_income
    )

    upfront_cost = (
        rent +
        deposit +
        application_fee
    )

    if monthly_income <= 0:
        return score

    ratio = (
        upfront_cost /
        monthly_income
    )

    # -------------------------
    # Extreme pressure
    # -------------------------

    if ratio > 3.0:

        reasons.append(
            (
                "Upfront costs are very "
                "high relative to income."
            )
        )

        actions.append(
            (
                "Ensure savings exist "
                "before applying."
            )
        )

        score = apply_score_change(

            score=score,

            breakdown=breakdown,

            title=(
                "Extreme upfront cost"
            ),

            delta=-10,

            details=(
                f"{ratio:.1f}x income"
            ),
        )

    # -------------------------
    # High pressure
    # -------------------------

    elif ratio > 2.0:

        reasons.append(
            (
                "Upfront costs may be "
                "difficult to mobilize."
            )
        )

        score = apply_score_change(

            score=score,

            breakdown=breakdown,

            title=(
                "High upfront cost"
            ),

            delta=-5,

            details=(
                f"{ratio:.1f}x income"
            ),
        )

    # -------------------------
    # Moderate pressure
    # -------------------------

    elif ratio > 1.2:

        reasons.append(
            (
                "Upfront costs are "
                "moderately high."
            )
        )

    return score

"""
Budget calculations.
"""


def suggested_budget_bands(
    monthly_income: int,
):
    """
    Calculate rental
    affordability bands.
    """

    monthly_income = max(
        0,
        int(monthly_income),
    )

    return {

        "conservative":
            int(
                monthly_income * 0.25
            ),

        "recommended":
            int(
                monthly_income * 0.33
            ),

        "upper_limit":
            int(
                monthly_income * 0.38
            ),
    }
