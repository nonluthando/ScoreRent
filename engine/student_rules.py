from typing import List

from engine.breakdown import apply_score_change
from engine.helpers import has_item

DOC_CLUSTERS = {
    "worker": [
        "bank statement",
        "payslip",
        "employment letter",
    ],

    "new_professional": [
        "employment contract",
        "offer letter",
        "bank statement",
        "guarantor letter",
    ],

    "student": [
        "bursary award letter",
        "nsfas award letter",
        "bursary confirmation",
        "proof of registration",
        "student ID",
        "guarantor letter",
    ],
}
def evaluate_student_support(
    score: int,
    breakdown: List,
    reasons: List[str],
    actions: List[str],

    renter_docs: set,

    monthly_income: int,

    rent: int,

    guarantor_monthly_income: int,

    is_bursary_student: bool,
):
    """
    Evaluate student-specific affordability
    and support pathways.

    Handles:

    - bursary students
    - non-bursary students
    - guarantor validation
    - affordability replacement

    Returns:

        (
            updated_score,
            effective_income,
            affordability_skip
        )
    """

    effective_income = monthly_income

    affordability_skip = False

    bursary_student = (
        is_bursary_student
    )

    non_bursary_student = (
        not is_bursary_student
    )

    # ---------------------------------
    # Non-bursary student logic
    # ---------------------------------

    if non_bursary_student:

        has_letter = any(
            (
                "letter" in doc and
                "guarantor" in doc
            )

            for doc in renter_docs
        )

        has_payslip = any(
            (
                "payslip" in doc and
                "guarantor" in doc
            )

            for doc in renter_docs
        )

        has_bank = any(
            (
                "bank" in doc and
                "guarantor" in doc
            )

            for doc in renter_docs
        )

        guarantor_docs_complete = (
            has_letter
            and has_payslip
            and has_bank
        )

        if (
            guarantor_docs_complete
            and guarantor_monthly_income > 0
        ):

            effective_income = (
                guarantor_monthly_income
            )

            score = apply_score_change(
                score=score,

                breakdown=breakdown,

                title=(
                    "Guarantor support"
                ),

                delta=18,

                details=(
                    f"Income: "
                    f"R{guarantor_monthly_income}"
                ),
            )

            reasons.append(
                (
                    "Application supported "
                    "by financially "
                    "qualified guarantor."
                )
            )

        else:

            score = apply_score_change(
                score=score,

                breakdown=breakdown,

                title=(
                    "Missing guarantor "
                    "support"
                ),

                delta=-45,
            )

            reasons.append(
                (
                    "Non-bursary students "
                    "usually require "
                    "guarantor support."
                )
            )

            actions.append(
                (
                    "Provide guarantor "
                    "letter, payslip, "
                    "and bank statements."
                )
            )

    # ---------------------------------
    # Bursary pathway
    # ---------------------------------

    else:

        affordability_skip = True

        has_bursary_proof = any(

            term in doc

            for doc in renter_docs

            for term in [

                "bursary",

                "nsfas",

                "award",
            ]
        )

        if not has_bursary_proof:

            score = apply_score_change(
                score=score,

                breakdown=breakdown,

                title=(
                    "Missing bursary "
                    "proof"
                ),

                delta=-35,
            )

            reasons.append(
                (
                    "Official bursary "
                    "documentation missing."
                )
            )

        shortfall = (
            rent -
            monthly_income
        )

        if shortfall > 0:

            score = apply_score_change(
                score=score,

                breakdown=breakdown,

                title=(
                    "Bursary shortfall"
                ),

                delta=-38,

                details=(
                    f"Shortfall: "
                    f"R{shortfall}"
                ),
            )

            reasons.append(
                (
                    "Bursary does not "
                    "fully cover rent."
                )
            )

            actions.append(
                (
                    "Add guarantor "
                    "income support."
                )
            )

        else:

            score = apply_score_change(
                score=score,

                breakdown=breakdown,

                title=(
                    "Bursary covers rent"
                ),

                delta=20,
            )

    return (
        score,
        effective_income,
        affordability_skip,
    )
