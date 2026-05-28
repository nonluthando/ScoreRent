"""
Cape Town Rental Application Evaluation Engine.

This module evaluates the likelihood of a rental application
being approved in the Cape Town rental market using:

- affordability analysis
- document completeness
- guarantor support
- area demand pressure
- bursary/student support logic

The evaluator returns:

- approval score
- confidence level
- actionable recommendations
- transparent scoring breakdown

"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Tuple


# ============================================================
# Market Configuration
# ============================================================

APP_MARKET = "Cape Town"

CURRENCY_CODE = "ZAR"
CURRENCY_SYMBOL = "R"

RECOMMENDED_RENT_TO_INCOME_CAP = 0.33
UPPER_RENT_TO_INCOME_CAP = 0.38
EXTREME_RENT_TO_INCOME_CAP = 0.45

MAX_AFFORDABILITY_PENALTY = 70

SEVERE_UPFRONT_COST_RATIO = 3.0
MODERATE_UPFRONT_COST_RATIO = 2.0
ELEVATED_UPFRONT_COST_RATIO = 1.2


# ============================================================
# Enums
# ============================================================

class RenterType(str, Enum):
    WORKER = "worker"
    NEW_PROFESSIONAL = "new_professional"
    STUDENT = "student"


class DemandLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ApplicationVerdict(str, Enum):
    STRONG_MATCH = "STRONG_MATCH"
    BORDERLINE = "BORDERLINE"
    HIGH_RISK = "HIGH_RISK"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ============================================================
# Result Models
# ============================================================

@dataclass
class EvaluationResult:
    """
    Final rental application assessment result.

    Attributes:
        score:
            Final application score between 0 and 100.

        verdict:
            Overall recommendation outcome.

        confidence:
            Confidence level of the evaluation.

        reasons:
            Key reasons influencing the result.

        actions:
            Recommended actions to improve approval chances.

        breakdown:
            Detailed scoring adjustments applied during evaluation.
    """

    score: int
    verdict: str
    confidence: str
    reasons: List[str]
    actions: List[str]
    breakdown: List[Dict[str, Any]]


# ============================================================
# Document Rules
# ============================================================

REQUIRED_DOCUMENT_CLUSTERS = {
    RenterType.WORKER.value: [
        "bank statement",
        "payslip",
        "employment letter",
    ],
    RenterType.NEW_PROFESSIONAL.value: [
        "employment contract",
        "offer letter",
        "bank statement",
        "guarantor letter",
    ],
    RenterType.STUDENT.value: [
        "bursary award letter",
        "nsfas award letter",
        "bursary confirmation",
        "proof of registration",
        "student ID",
        "guarantor letter",
    ],
}


# ============================================================
# Currency Helpers
# ============================================================

def normalize_currency(value: Any) -> int:
    """
    Safely normalize currency-like values into positive integers.

    Invalid or negative values return 0.
    """

    try:
        return max(0, int(round(float(value))))
    except Exception:
        return 0


def format_currency_zar(value: int) -> str:
    """
    Format integer currency values into South African Rand format.

    Example:
        12500 -> R12 500
    """

    value = normalize_currency(value)
    return f"{CURRENCY_SYMBOL}{value:,}".replace(",", " ")


# ============================================================
# Budget Guidance
# ============================================================

def calculate_budget_bands(monthly_income: int) -> Dict[str, int]:
    """
    Calculate recommended rental budget ranges for Cape Town.

    Args:
        monthly_income:
            Applicant's verified monthly income.

    Returns:
        Dictionary containing:
            - conservative
            - recommended
            - upper_limit
    """

    monthly_income = normalize_currency(monthly_income)

    return {
        "conservative": int(monthly_income * 0.25),
        "recommended": int(
            monthly_income * RECOMMENDED_RENT_TO_INCOME_CAP
        ),
        "upper_limit": int(
            monthly_income * UPPER_RENT_TO_INCOME_CAP
        ),
    }


# ============================================================
# Utility Helpers
# ============================================================

def deduplicate_preserve_order(items: List[str]) -> List[str]:
    """
    Remove duplicates while preserving original order.
    """

    return list(dict.fromkeys(items))


def calculate_ratio_percentage(
    numerator: int,
    denominator: int,
) -> float:
    """
    Calculate percentage ratio safely.

    Returns 999.0 if denominator is zero or invalid.
    """

    if denominator <= 0:
        return 999.0

    return (numerator / denominator) * 100.0


def contains_text(
    items: List[str],
    text: str,
) -> bool:
    """
    Check whether a normalized string exists in a list.
    """

    target = text.strip().lower()

    return any(
        item.strip().lower() == target
        for item in items
    )


def append_score_breakdown(
    score_breakdown: List[Dict[str, Any]],
    title: str,
    score_delta: int,
    score_before: int,
    score_after: int,
    details: str = "",
) -> None:
    """
    Append scoring adjustment details to breakdown log.
    """

    score_breakdown.append(
        {
            "title": title,
            "delta": int(score_delta),
            "before": int(score_before),
            "after": int(score_after),
            "details": details,
        }
    )


def apply_score_adjustment(
    current_score: int,
    score_breakdown: List[Dict[str, Any]],
    title: str,
    score_delta: int,
    details: str = "",
) -> int:
    """
    Apply score adjustment and log it to breakdown history.
    """

    score_before = current_score
    score_after = current_score + int(score_delta)

    append_score_breakdown(
        score_breakdown=score_breakdown,
        title=title,
        score_delta=score_delta,
        score_before=score_before,
        score_after=score_after,
        details=details,
    )

    return score_after


def add_reason(
    reasons: List[str],
    message: str,
) -> None:
    """
    Add unique explanatory reason.
    """

    if not contains_text(reasons, message):
        reasons.append(message)


def add_action(
    actions: List[str],
    message: str,
) -> None:
    """
    Add unique recommended action.
    """

    if not contains_text(actions, message):
        actions.append(message)


def trim_output_lists(
    reasons: List[str],
    actions: List[str],
) -> Tuple[List[str], List[str]]:
    """
    Limit response payload size while preserving ordering.
    """

    reasons = deduplicate_preserve_order(reasons)[:5]
    actions = deduplicate_preserve_order(actions)[:4]

    return reasons, actions


# ============================================================
# Main Evaluation Engine
# ============================================================

def evaluate_rental_application(
    renter_type: str,
    monthly_income: int,
    submitted_documents: List[str],
    monthly_rent: int,
    security_deposit: int,
    application_fee: int,
    required_documents: List[str],
    area_demand: str,
    guarantor_monthly_income: int = 0,
    is_bursary_student: bool = False,
) -> Tuple[EvaluationResult, Dict[str, int]]:
    """
    Evaluate a rental application's approval likelihood.

    The evaluation considers:

    - affordability ratios
    - Cape Town market thresholds
    - document completeness
    - student/guarantor support
    - demand pressure in the target area

    Args:
        renter_type:
            Applicant category.

        monthly_income:
            Verified applicant income.

        submitted_documents:
            Documents supplied by applicant.

        monthly_rent:
            Target property's monthly rent.

        security_deposit:
            Required upfront deposit.

        application_fee:
            Non-refundable application fee.

        required_documents:
            Documents required by landlord or agency.

        area_demand:
            Rental demand level for the area.

        guarantor_monthly_income:
            Monthly income of guarantor if applicable.

        is_bursary_student:
            Indicates whether student receives bursary funding.

    Returns:
        Tuple containing:
            - EvaluationResult
            - Suggested rental budget bands
    """

    # --------------------------------------------------------
    # Normalize financial values
    # --------------------------------------------------------

    monthly_income = normalize_currency(monthly_income)
    monthly_rent = normalize_currency(monthly_rent)
    security_deposit = normalize_currency(security_deposit)
    application_fee = normalize_currency(application_fee)
    guarantor_monthly_income = normalize_currency(
        guarantor_monthly_income
    )

    # --------------------------------------------------------
    # Initialize response containers
    # --------------------------------------------------------

    reasons: List[str] = []
    actions: List[str] = []
    score_breakdown: List[Dict[str, Any]] = []

    # --------------------------------------------------------
    # Normalize enums
    # --------------------------------------------------------

    renter_type = (renter_type or "").strip().lower()

    if renter_type not in [
        member.value for member in RenterType
    ]:
        renter_type = RenterType.WORKER.value

    area_demand = (area_demand or "MEDIUM").upper()

    if area_demand not in [
        member.value for member in DemandLevel
    ]:
        area_demand = DemandLevel.MEDIUM.value

    submitted_documents_set = {
        document.strip().lower()
        for document in submitted_documents or []
    }

    required_documents_set = {
        document.strip().lower()
        for document in required_documents or []
    }

    # --------------------------------------------------------
    # Applicant classification
    # --------------------------------------------------------

    is_student = renter_type == RenterType.STUDENT.value

    bursary_student = (
        is_student and is_bursary_student
    )

    non_bursary_student = (
        is_student and not is_bursary_student
    )

    # --------------------------------------------------------
    # Base score
    # --------------------------------------------------------

    score = 100

    append_score_breakdown(
        score_breakdown=score_breakdown,
        title="Base match score",
        score_delta=0,
        score_before=0,
        score_after=score,
        details=(
            f"Evaluation calibrated for "
            f"{APP_MARKET} rental market (2026)."
        ),
    )

    qualifying_income = monthly_income

    # ========================================================
    # Non-bursary Student Guarantor Logic
    # ========================================================

    if non_bursary_student:

        has_guarantor_letter = any(
            "letter" in document and "guarantor" in document
            for document in submitted_documents_set
        )

        has_guarantor_payslip = any(
            "payslip" in document and "guarantor" in document
            for document in submitted_documents_set
        )

        has_guarantor_bank_statement = any(
            "bank" in document and "guarantor" in document
            for document in submitted_documents_set
        )

        guarantor_documents_complete = all([
            has_guarantor_letter,
            has_guarantor_payslip,
            has_guarantor_bank_statement,
        ])

        if (
            guarantor_documents_complete
            and guarantor_monthly_income > 0
        ):

            qualifying_income = guarantor_monthly_income

            score = apply_score_adjustment(
                current_score=score,
                score_breakdown=score_breakdown,
                title="Qualified guarantor support",
                score_delta=18,
                details=(
                    "Guarantor income: "
                    f"{format_currency_zar(guarantor_monthly_income)}"
                ),
            )

            add_reason(
                reasons,
                (
                    "Application supported by a financially "
                    "qualified guarantor."
                ),
            )

        else:

            score = apply_score_adjustment(
                current_score=score,
                score_breakdown=score_breakdown,
                title="Missing guarantor support",
                score_delta=-45,
            )

            add_reason(
                reasons,
                (
                    "Non-bursary students typically require "
                    "full guarantor support."
                ),
            )

            add_action(
                actions,
                (
                    "Provide guarantor letter, payslip, "
                    "and bank statements."
                ),
            )

    # ========================================================
    # Bursary Student Logic
    # ========================================================

    skip_affordability_evaluation = False

    if bursary_student:

        skip_affordability_evaluation = True

        has_bursary_proof = any(
            keyword in document
            for document in submitted_documents_set
            for keyword in ["bursary", "nsfas", "award"]
        )

        if not has_bursary_proof:

            score = apply_score_adjustment(
                current_score=score,
                score_breakdown=score_breakdown,
                title="Missing bursary confirmation",
                score_delta=-35,
            )

            add_reason(
                reasons,
                (
                    "Official bursary award documentation "
                    "is missing."
                ),
            )

        monthly_rent_shortfall = (
            monthly_rent - monthly_income
        )

        if monthly_rent_shortfall > 0:

            score = apply_score_adjustment(
                current_score=score,
                score_breakdown=score_breakdown,
                title="Bursary funding shortfall",
                score_delta=-38,
                details=(
                    "Monthly shortfall: "
                    f"{format_currency_zar(monthly_rent_shortfall)}"
                ),
            )

            add_reason(
                reasons,
                (
                    "Bursary funding does not fully "
                    "cover monthly rent."
                ),
            )

            add_action(
                actions,
                (
                    "Add guarantor income to strengthen "
                    "the application."
                ),
            )

        else:

            score = apply_score_adjustment(
                current_score=score,
                score_breakdown=score_breakdown,
                title="Bursary fully covers rent",
                score_delta=20,
            )

    # ========================================================
    # Affordability Analysis
    # ========================================================

    if not skip_affordability_evaluation:

        rent_to_income_ratio = (
            calculate_ratio_percentage(
                monthly_rent,
                qualifying_income,
            ) / 100.0
        )

        if (
            rent_to_income_ratio
            <= RECOMMENDED_RENT_TO_INCOME_CAP
        ):

            add_reason(
                reasons,
                (
                    "Rent falls within recommended "
                    "Cape Town affordability guidelines."
                ),
            )

        else:

            affordability_risk_range = (
                EXTREME_RENT_TO_INCOME_CAP
                - RECOMMENDED_RENT_TO_INCOME_CAP
            )

            affordability_excess_ratio = (
                min(
                    rent_to_income_ratio,
                    EXTREME_RENT_TO_INCOME_CAP,
                )
                - RECOMMENDED_RENT_TO_INCOME_CAP
            )

            proportional_penalty = int(
                (
                    affordability_excess_ratio
                    / affordability_risk_range
                )
                * MAX_AFFORDABILITY_PENALTY
            )

            score = apply_score_adjustment(
                current_score=score,
                score_breakdown=score_breakdown,
                title="Affordability risk",
                score_delta=-proportional_penalty,
                details=(
                    f"{rent_to_income_ratio * 100:.0f}% "
                    "rent-to-income ratio"
                ),
            )

            if (
                rent_to_income_ratio
                >= EXTREME_RENT_TO_INCOME_CAP
            ):

                add_reason(
                    reasons,
                    (
                        "Rent is significantly above "
                        "typical approval thresholds "
                        "for Cape Town."
                    ),
                )

    # ========================================================
    # Required Documents
    # ========================================================

    missing_required_documents = (
        required_documents_set
        - submitted_documents_set
    )

    if missing_required_documents:

        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Missing required documents",
            score_delta=-20,
            details=(
                ", ".join(sorted(missing_required_documents))
            ),
        )

    # ========================================================
    # Area Demand Risk
    # ========================================================

    if area_demand == DemandLevel.HIGH.value:

        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="High-demand rental area",
            score_delta=-10,
        )

    elif area_demand == DemandLevel.LOW.value:

        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Lower competition rental area",
            score_delta=5,
        )

    # ========================================================
    # Upfront Cost Risk Warnings
    # ========================================================

    if monthly_income > 0:

        total_upfront_cost = (
            monthly_rent
            + security_deposit
            + application_fee
        )

        upfront_cost_ratio = (
            total_upfront_cost / monthly_income
        )

        if (
            upfront_cost_ratio
            > SEVERE_UPFRONT_COST_RATIO
        ):

            add_reason(
                reasons,
                (
                    "Upfront rental costs are extremely "
                    "high relative to income."
                ),
            )

            add_action(
                actions,
                (
                    "Ensure sufficient savings are "
                    "available before applying."
                ),
            )

        elif (
            upfront_cost_ratio
            > MODERATE_UPFRONT_COST_RATIO
        ):

            add_reason(
                reasons,
                (
                    "Upfront rental costs may be difficult "
                    "to mobilize quickly."
                ),
            )

        elif (
            upfront_cost_ratio
            > ELEVATED_UPFRONT_COST_RATIO
        ):

            add_reason(
                reasons,
                (
                    "Upfront rental costs are moderately "
                    "high relative to income."
                ),
            )

    # ========================================================
    # Final Score Normalization
    # ========================================================

    score = max(0, min(100, score))

    # ========================================================
    # Final Verdict
    # ========================================================

    if score >= 75:

        verdict = ApplicationVerdict.STRONG_MATCH.value
        confidence = ConfidenceLevel.HIGH.value

    elif score >= 55:

        verdict = ApplicationVerdict.BORDERLINE.value
        confidence = ConfidenceLevel.MEDIUM.value

    else:

        verdict = ApplicationVerdict.HIGH_RISK.value
        confidence = ConfidenceLevel.LOW.value

    append_score_breakdown(
        score_breakdown=score_breakdown,
        title="Final verdict",
        score_delta=0,
        score_before=score,
        score_after=score,
        details=f"{verdict} ({confidence})",
    )

    # ========================================================
    # Output Cleanup
    # ========================================================

    reasons, actions = trim_output_lists(
        reasons,
        actions,
    )

    return (
        EvaluationResult(
            score=score,
            verdict=verdict,
            confidence=confidence,
            reasons=reasons,
            actions=actions,
            breakdown=score_breakdown,
        ),
        calculate_budget_bands(qualifying_income),
    )
