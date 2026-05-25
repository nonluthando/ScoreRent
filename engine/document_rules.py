from typing import List, Set

from engine.breakdown import apply_score_change


def evaluate_required_documents(
    score: int,
    breakdown: List,
    reasons: List[str],
    actions: List[str],

    renter_docs: Set[str],

    required_docs: Set[str],
):
    """
    Evaluate listing document requirements.

    Applies penalties when required
    documents are missing.

    Returns:
        updated_score
    """

    missing_required = (
        required_docs -
        renter_docs
    )

    if not missing_required:
        return score

    score = apply_score_change(

        score=score,

        breakdown=breakdown,

        title=(
            "Missing required "
            "documents"
        ),

        delta=-20,

        details=(
            f"{len(missing_required)} "
            "documents missing"
        ),
    )

    missing_list = sorted(
        list(
            missing_required
        )
    )

    reasons.append(
        (
            "Required listing "
            "documents are missing."
        )
    )

    actions.append(
        (
            "Upload missing documents: "
            + ", ".join(
                missing_list
            )
        )
    )

    return score
