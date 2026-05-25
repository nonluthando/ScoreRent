from typing import List

from engine.breakdown import push_breakdown


def determine_verdict(
    score: int,
    breakdown: List,
):
    """
    Determine recommendation outcome
    from final evaluation score.

    Categories:

    HIGH:
        75+

    MEDIUM:
        55-74

    LOW:
        below 55

    Returns:

        (
            verdict,
            confidence
        )
    """

    score = max(
        0,
        min(
            100,
            score,
        )
    )

    if score >= 75:

        verdict = (
            "WORTH_APPLYING"
        )

        confidence = "HIGH"

    elif score >= 55:

        verdict = (
            "BORDERLINE"
        )

        confidence = "MEDIUM"

    else:

        verdict = (
            "NOT_WORTH_IT"
        )

        confidence = "LOW"

    push_breakdown(

        breakdown=breakdown,

        title=(
            "Final verdict"
        ),

        delta=0,

        before=score,

        after=score,

        details=(
            f"{verdict} "
            f"({confidence})"
        ),
    )

    return (
        score,
        verdict,
        confidence,
    )
