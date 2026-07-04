"""
Cape Town Rental Application Evaluation Engine.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Set, Tuple


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

# ============================================================
# Required Document Clusters
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
    score: int
    verdict: str
    confidence: str
    reasons: List[str]
    actions: List[str]
    breakdown: List[Dict[str, Any]]


@dataclass
class EvaluationInput:
    renter_type: str
    monthly_income: int
    submitted_documents: Set[str]
    monthly_rent: int
    security_deposit: int
    application_fee: int
    required_documents: Set[str]
    area_demand: str
    guarantor_monthly_income: int
    is_bursary_student: bool

    @property
    def is_student(self) -> bool:
        return self.renter_type == RenterType.STUDENT.value

    @property
    def bursary_student(self) -> bool:
        return self.is_student and self.is_bursary_student

    @property
    def non_bursary_student(self) -> bool:
        return self.is_student and not self.is_bursary_student


# ============================================================
# Currency Helpers
# ============================================================

def normalize_currency(value: Any) -> int:
    try:
        return max(0, int(round(float(value))))
    except Exception:
        return 0


def format_currency_zar(value: int) -> str:
    value = normalize_currency(value)
    return f"{CURRENCY_SYMBOL}{value:,}".replace(",", " ")


# ============================================================
# Normalization Helpers
# ============================================================

def normalize_renter_type(renter_type: str) -> str:
    renter_type = (renter_type or "").strip().lower()
    valid_types = [member.value for member in RenterType]

    if renter_type not in valid_types:
        return RenterType.WORKER.value

    return renter_type


def normalize_area_demand(area_demand: str) -> str:
    area_demand = (area_demand or "MEDIUM").upper()
    valid_levels = [member.value for member in DemandLevel]

    if area_demand not in valid_levels:
        return DemandLevel.MEDIUM.value

    return area_demand


def normalize_document_set(documents: List[str]) -> Set[str]:
    return {
        document.strip().lower()
        for document in documents or []
    }


def build_evaluation_input(
    renter_type: str,
    monthly_income: int,
    submitted_documents: List[str],
    monthly_rent: int,
    security_deposit: int,
    application_fee: int,
    required_documents: List[str],
    area_demand: str,
    guarantor_monthly_income: int,
    is_bursary_student: bool,
) -> EvaluationInput:
    return EvaluationInput(
        renter_type=normalize_renter_type(renter_type),
        monthly_income=normalize_currency(monthly_income),
        submitted_documents=normalize_document_set(submitted_documents),
        monthly_rent=normalize_currency(monthly_rent),
        security_deposit=normalize_currency(security_deposit),
        application_fee=normalize_currency(application_fee),
        required_documents=normalize_document_set(required_documents),
        area_demand=normalize_area_demand(area_demand),
        guarantor_monthly_income=normalize_currency(guarantor_monthly_income),
        is_bursary_student=is_bursary_student,
    )


# ============================================================
# Budget Guidance
# ============================================================

def calculate_budget_bands(monthly_income: int) -> Dict[str, int]:
    monthly_income = normalize_currency(monthly_income)

    return {
        "conservative": int(monthly_income * 0.25),
        "recommended": int(monthly_income * RECOMMENDED_RENT_TO_INCOME_CAP),
        "upper_limit": int(monthly_income * UPPER_RENT_TO_INCOME_CAP),
    }


# ============================================================
# Utility Helpers
# ============================================================

def deduplicate_preserve_order(items: List[str]) -> List[str]:
    return list(dict.fromkeys(items))


def calculate_ratio_percentage(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 999.0

    return (numerator / denominator) * 100.0


def contains_text(items: List[str], text: str) -> bool:
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


def add_reason(reasons: List[str], message: str) -> None:
    if not contains_text(reasons, message):
        reasons.append(message)


def add_action(actions: List[str], message: str) -> None:
    if not contains_text(actions, message):
        actions.append(message)


def trim_output_lists(
    reasons: List[str],
    actions: List[str],
) -> Tuple[List[str], List[str]]:
    reasons = deduplicate_preserve_order(reasons)[:5]
    actions = deduplicate_preserve_order(actions)[:4]

    return reasons, actions


def clamp_score(score: int) -> int:
    return max(0, min(100, score))


# ============================================================
# Guarantor Helpers
# ============================================================

def has_complete_guarantor_documents(submitted_documents: Set[str]) -> bool:
    has_guarantor_letter = any(
        "letter" in document and "guarantor" in document
        for document in submitted_documents
    )

    has_guarantor_payslip = any(
        "payslip" in document and "guarantor" in document
        for document in submitted_documents
    )

    has_guarantor_bank_statement = any(
        "bank" in document and "guarantor" in document
        for document in submitted_documents
    )

    return all([
        has_guarantor_letter,
        has_guarantor_payslip,
        has_guarantor_bank_statement,
    ])


def evaluate_non_bursary_student_guarantor(
    score: int,
    qualifying_income: int,
    inputs: EvaluationInput,
    reasons: List[str],
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> Tuple[int, int]:
    guarantor_documents_complete = has_complete_guarantor_documents(
        inputs.submitted_documents
    )

    if guarantor_documents_complete and inputs.guarantor_monthly_income > 0:
        qualifying_income = inputs.guarantor_monthly_income

        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Qualified guarantor support",
            score_delta=18,
            details=(
                "Guarantor income: "
                f"{format_currency_zar(inputs.guarantor_monthly_income)}"
            ),
        )

        add_reason(
            reasons,
            "Application supported by a financially qualified guarantor.",
        )

        return score, qualifying_income

    score = apply_score_adjustment(
        current_score=score,
        score_breakdown=score_breakdown,
        title="Missing guarantor support",
        score_delta=-45,
    )

    add_reason(
        reasons,
        "Non-bursary students typically require full guarantor support.",
    )

    add_action(
        actions,
        "Provide guarantor letter, payslip, and bank statements.",
    )

    return score, qualifying_income


# ============================================================
# Bursary Student Logic
# ============================================================

def has_bursary_proof(submitted_documents: Set[str]) -> bool:
    return any(
        keyword in document
        for document in submitted_documents
        for keyword in ["bursary", "nsfas", "award"]
    )


def evaluate_bursary_student(
    score: int,
    inputs: EvaluationInput,
    reasons: List[str],
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> Tuple[int, bool]:
    skip_affordability_evaluation = True

    if not has_bursary_proof(inputs.submitted_documents):
        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Missing bursary confirmation",
            score_delta=-35,
        )

        add_reason(
            reasons,
            "Official bursary award documentation is missing.",
        )

    monthly_rent_shortfall = inputs.monthly_rent - inputs.monthly_income

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
            "Bursary funding does not fully cover monthly rent.",
        )

        add_action(
            actions,
            "Add guarantor income to strengthen the application.",
        )

        return score, skip_affordability_evaluation

    score = apply_score_adjustment(
        current_score=score,
        score_breakdown=score_breakdown,
        title="Bursary fully covers rent",
        score_delta=20,
    )

    return score, skip_affordability_evaluation


# ============================================================
# Affordability Logic
# ============================================================

def evaluate_affordability(
    score: int,
    monthly_rent: int,
    qualifying_income: int,
    reasons: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> int:
    rent_to_income_ratio = (
        calculate_ratio_percentage(monthly_rent, qualifying_income) / 100.0
    )

    if rent_to_income_ratio <= RECOMMENDED_RENT_TO_INCOME_CAP:
        add_reason(
            reasons,
            "Rent falls within recommended Cape Town affordability guidelines.",
        )
        return score

    affordability_risk_range = (
        EXTREME_RENT_TO_INCOME_CAP - RECOMMENDED_RENT_TO_INCOME_CAP
    )

    affordability_excess_ratio = (
        min(rent_to_income_ratio, EXTREME_RENT_TO_INCOME_CAP)
        - RECOMMENDED_RENT_TO_INCOME_CAP
    )

    proportional_penalty = int(
        (affordability_excess_ratio / affordability_risk_range)
        * MAX_AFFORDABILITY_PENALTY
    )

    score = apply_score_adjustment(
        current_score=score,
        score_breakdown=score_breakdown,
        title="Affordability risk",
        score_delta=-proportional_penalty,
        details=f"{rent_to_income_ratio * 100:.0f}% rent-to-income ratio",
    )

    if rent_to_income_ratio >= EXTREME_RENT_TO_INCOME_CAP:
        add_reason(
            reasons,
            "Rent is significantly above typical approval thresholds for Cape Town.",
        )

    return score


# ============================================================
# Document Logic
# ============================================================

def evaluate_required_documents(
    score: int,
    required_documents: Set[str],
    submitted_documents: Set[str],
    score_breakdown: List[Dict[str, Any]],
) -> int:
    missing_required_documents = required_documents - submitted_documents

    if not missing_required_documents:
        return score

    return apply_score_adjustment(
        current_score=score,
        score_breakdown=score_breakdown,
        title="Missing required documents",
        score_delta=-20,
        details=", ".join(sorted(missing_required_documents)),
    )


# ============================================================
# Area Demand Logic
# ============================================================

def evaluate_area_demand(
    score: int,
    area_demand: str,
    score_breakdown: List[Dict[str, Any]],
) -> int:
    if area_demand == DemandLevel.HIGH.value:
        return apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="High-demand rental area",
            score_delta=-10,
        )

    if area_demand == DemandLevel.LOW.value:
        return apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Lower competition rental area",
            score_delta=5,
        )

    return score


# ============================================================
# Upfront Cost Logic
# ============================================================

def add_upfront_cost_warnings(
    inputs: EvaluationInput,
    reasons: List[str],
    actions: List[str],
) -> None:
    if inputs.monthly_income <= 0:
        return

    total_upfront_cost = (
        inputs.monthly_rent
        + inputs.security_deposit
        + inputs.application_fee
    )

    upfront_cost_ratio = total_upfront_cost / inputs.monthly_income

    if upfront_cost_ratio > SEVERE_UPFRONT_COST_RATIO:
        add_reason(
            reasons,
            "Upfront rental costs are extremely high relative to income.",
        )

        add_action(
            actions,
            "Ensure sufficient savings are available before applying.",
        )

    elif upfront_cost_ratio > MODERATE_UPFRONT_COST_RATIO:
        add_reason(
            reasons,
            "Upfront rental costs may be difficult to mobilize quickly.",
        )

    elif upfront_cost_ratio > ELEVATED_UPFRONT_COST_RATIO:
        add_reason(
            reasons,
            "Upfront rental costs are moderately high relative to income.",
        )


# ============================================================
# Verdict Logic
# ============================================================

def determine_verdict(score: int) -> Tuple[str, str]:
    if score >= 75:
        return (
            ApplicationVerdict.STRONG_MATCH.value,
            ConfidenceLevel.HIGH.value,
        )

    if score >= 55:
        return (
            ApplicationVerdict.BORDERLINE.value,
            ConfidenceLevel.MEDIUM.value,
        )

    return (
        ApplicationVerdict.HIGH_RISK.value,
        ConfidenceLevel.LOW.value,
    )


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
    inputs = build_evaluation_input(
        renter_type=renter_type,
        monthly_income=monthly_income,
        submitted_documents=submitted_documents,
        monthly_rent=monthly_rent,
        security_deposit=security_deposit,
        application_fee=application_fee,
        required_documents=required_documents,
        area_demand=area_demand,
        guarantor_monthly_income=guarantor_monthly_income,
        is_bursary_student=is_bursary_student,
    )

    reasons: List[str] = []
    actions: List[str] = []
    score_breakdown: List[Dict[str, Any]] = []

    score = 100
    qualifying_income = inputs.monthly_income
    skip_affordability_evaluation = False

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

    if inputs.non_bursary_student:
        score, qualifying_income = evaluate_non_bursary_student_guarantor(
            score=score,
            qualifying_income=qualifying_income,
            inputs=inputs,
            reasons=reasons,
            actions=actions,
            score_breakdown=score_breakdown,
        )

    if inputs.bursary_student:
        score, skip_affordability_evaluation = evaluate_bursary_student(
            score=score,
            inputs=inputs,
            reasons=reasons,
            actions=actions,
            score_breakdown=score_breakdown,
        )

    if not skip_affordability_evaluation:
        score = evaluate_affordability(
            score=score,
            monthly_rent=inputs.monthly_rent,
            qualifying_income=qualifying_income,
            reasons=reasons,
            score_breakdown=score_breakdown,
        )

    score = evaluate_required_documents(
        score=score,
        required_documents=inputs.required_documents,
        submitted_documents=inputs.submitted_documents,
        score_breakdown=score_breakdown,
    )

    score = evaluate_area_demand(
        score=score,
        area_demand=inputs.area_demand,
        score_breakdown=score_breakdown,
    )

    add_upfront_cost_warnings(
        inputs=inputs,
        reasons=reasons,
        actions=actions,
    )

    score = clamp_score(score)

    verdict, confidence = determine_verdict(score)

    append_score_breakdown(
        score_breakdown=score_breakdown,
        title="Final verdict",
        score_delta=0,
        score_before=score,
        score_after=score,
        details=f"{verdict} ({confidence})",
    )

    reasons, actions = trim_output_lists(reasons, actions)

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
