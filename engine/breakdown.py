from typing import Dict, List


def push_breakdown(
    breakdown: List[
        Dict
    ],

    title: str,

    delta: int,

    before: int,

    after: int,

    details: str = "",
):
    """
    Add explainability event.
    """

    breakdown.append(

        {
            "title": title,

            "delta": int(
                delta
            ),

            "before": int(
                before
            ),

            "after": int(
                after
            ),

            "details": details,
        }

    )


def apply_score_change(
    score: int,

    breakdown,

    title,

    delta,

    details="",
):
    """
    Apply score modification.
    """

    before = score

    after = score + int(
        delta
    )

    push_breakdown(
        breakdown,
        title,
        delta,
        before,
        after,
        details,
    )

    return after
