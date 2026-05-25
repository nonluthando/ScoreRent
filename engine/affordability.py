from typing import List

from engine.helpers import ratio_pct
from engine.breakdown import apply_score_change
from engine.config import (
    CAPE_TOWN_RECOMMENDED_CAP,
    CAPE_TOWN_EXTREME_CAP,
)


def evaluate_affordability(
    score: int,
    breakdown: List,
    reasons: List[str],
    monthly_income: int,
    rent: int,
):
    """
    Evaluate rental affordability.

    Applies proportional penalties when
    rent exceeds recommended affordability
    thresholds.

    Returns:
        updated_score
    """

    if monthly_income <= 0:
        return score

    pct = (
        ratio_pct(
            rent,
            monthly_income,
        )
        / 100.0
    )

    recommended = (
        CAPE_TOWN_RECOMMENDED_CAP
    )

    extreme = (
        CAPE_TOWN_EXTREME_CAP
    )

    if pct <= recommended:

        reasons.append(
            (
                "Rent is within "
                "recommended affordability "
                "range."
            )
        )

        return score

    max_penalty = 70

    risk_range = (
        extreme -
        recommended
    )

    over_ratio = min(
        pct,
        extreme,
    ) - recommended

    proportional_penalty = int(
        (
            over_ratio /
            risk_range
        )
        * max_penalty
    )

    score = apply_score_change(
        score=score,

        breakdown=breakdown,

        title=(
            "Affordability risk "
            "(proportional)"
        ),

        delta=(
            -proportional_penalty
        ),

        details=(
            f"{pct*100:.0f}% "
            "of income"
        ),
    )

    reasons.append(
        (
            "Rent exceeds "
            "recommended "
            "approval range."
        )
    )

    return score
