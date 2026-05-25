from typing import List

from engine.breakdown import apply_score_change


def evaluate_market_demand(
    score: int,
    breakdown: List,
    reasons: List[str],

    area_demand: str,
):
    """
    Evaluate market competition risk.

    Higher demand areas reduce confidence
    because competition is stronger.

    Lower demand areas slightly improve
    confidence.

    Args:
        score:
            Current evaluation score.

        breakdown:
            Explainability events.

        reasons:
            Human-readable reasons.

        area_demand:
            LOW / MEDIUM / HIGH

    Returns:
        Updated score
    """

    demand = (
        area_demand
        .strip()
        .upper()
    )

    if demand == "HIGH":

        score = apply_score_change(

            score=score,

            breakdown=breakdown,

            title=(
                "High demand area"
            ),

            delta=-10,

            details=(
                "Competition risk increased"
            ),
        )

        reasons.append(
            (
                "Area has high rental "
                "competition."
            )
        )

    elif demand == "LOW":

        score = apply_score_change(

            score=score,

            breakdown=breakdown,

            title=(
                "Low demand area"
            ),

            delta=5,

            details=(
                "Lower competition"
            ),
        )

        reasons.append(
            (
                "Lower competition "
                "may improve chances."
            )
        )

    return score
