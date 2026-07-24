"""
Cape Town Rental Application Evaluation Engine.

The engine is deterministic and explainable: every score change is recorded in
an ordered breakdown, and the final score is clamped only after all rules run.
"""

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


APP_MARKET = "Cape Town"

CURRENCY_CODE = "ZAR"
CURRENCY_SYMBOL = "R"

RECOMMENDED_RENT_TO_INCOME_CAP = 0.33
UPPER_RENT_TO_INCOME_CAP = 0.38
EXTREME_RENT_TO_INCOME_CAP = 0.45

MAX_AFFORDABILITY_PENALTY = 70
MISSING_RENT_PENALTY = 70

SEVERE_UPFRONT_COST_RATIO = 3.0
MODERATE_UPFRONT_COST_RATIO = 2.0
ELEVATED_UPFRONT_COST_RATIO = 1.2

MODERATE_UPFRONT_COST_PENALTY = 8
SEVERE_UPFRONT_COST_PENALTY = 15

PROFILE_DOCUMENT_PENALTY_PER_GROUP = 8
MAX_PROFILE_DOCUMENT_PENALTY = 24
REQUIRED_DOCUMENT_PENALTY_PER_DOCUMENT = 10
OVERLAPPING_REQUIRED_DOCUMENT_PENALTY = 4
MAX_REQUIRED_DOCUMENT_PENALTY = 30


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


REQUIRED_DOCUMENT_CLUSTERS = {
    RenterType.WORKER.value: [
        ["bank statement"],
        ["payslip"],
    ],
    RenterType.NEW_PROFESSIONAL.value: [
        ["employment contract", "offer letter"],
        ["bank statement"],
    ],
    # Separate groups mean students are expected to have both documents.
    RenterType.STUDENT.value: [
        ["proof of registration"],
        ["student id"],
    ],
}


DOCUMENT_ALIASES = {
    "bank statement": [
        "bank statement",
        "bank statements",
        "3 months bank statement",
        "3 months bank statements",
        "three months bank statement",
        "three months bank statements",
        "banking statement",
    ],
    "payslip": [
        "payslip",
        "pay slip",
        "latest payslip",
        "salary slip",
        "proof of income",
    ],
    "employment letter": [
        "employment letter",
        "letter of employment",
        "employer letter",
        "confirmation of employment",
    ],
    "employment contract": [
        "employment contract",
        "work contract",
        "contract of employment",
    ],
    "offer letter": [
        "offer letter",
        "job offer",
        "employment offer",
    ],
    "guarantor letter": [
        "guarantor letter",
        "surety letter",
        "sponsor letter",
    ],
    "guarantor payslip": [
        "guarantor payslip",
        "guarantor pay slip",
        "guarantor salary slip",
    ],
    "guarantor bank statement": [
        "guarantor bank statement",
        "guarantor bank statements",
    ],
    "bursary award letter": [
        "bursary award letter",
        "bursary letter",
        "bursary confirmation",
        "funding letter",
        "funding confirmation",
    ],
    "nsfas award letter": [
        "nsfas award letter",
        "nsfas confirmation",
        "nsfas funding letter",
    ],
    "proof of registration": [
        "proof of registration",
        "registration proof",
        "student registration",
    ],
    "student id": [
        "student id",
        "student card",
        "student number",
    ],
}


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

    renter_type_was_valid: bool
    area_demand_was_provided: bool
    area_demand_was_valid: bool
    monthly_income_was_valid: bool
    monthly_rent_was_valid: bool
    security_deposit_was_valid: bool
    application_fee_was_valid: bool
    guarantor_income_was_valid: bool
    bursary_flag_was_valid: bool

    @property
    def is_student(self) -> bool:
        return self.renter_type == RenterType.STUDENT.value

    @property
    def bursary_student(self) -> bool:
        return self.is_student and self.is_bursary_student

    @property
    def non_bursary_student(self) -> bool:
        return self.is_student and not self.is_bursary_student


# ---------------------------------------------------------------------------
# Normalisation and validation
# ---------------------------------------------------------------------------


def normalize_document_text(document: str) -> str:
    return " ".join((document or "").strip().lower().split())


def _build_alias_lookup() -> Dict[str, str]:
    lookup: Dict[str, str] = {}

    for canonical, aliases in DOCUMENT_ALIASES.items():
        canonical_normalized = normalize_document_text(canonical)
        lookup[canonical_normalized] = canonical_normalized

        for alias in aliases:
            lookup[normalize_document_text(alias)] = canonical_normalized

    return lookup


DOCUMENT_ALIAS_TO_CANONICAL = _build_alias_lookup()


def canonicalize_document(document: str) -> str:
    normalized = normalize_document_text(document)
    return DOCUMENT_ALIAS_TO_CANONICAL.get(normalized, normalized)


def parse_currency(value: Any) -> Tuple[int, bool]:
    """Return a non-negative integer and whether the original value was valid."""
    if value is None or isinstance(value, bool):
        return 0, False

    if isinstance(value, str) and not value.strip():
        return 0, False

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return 0, False

    if not math.isfinite(numeric_value) or numeric_value < 0:
        return 0, False

    return int(round(numeric_value)), True


def normalize_currency(value: Any) -> int:
    normalized, _ = parse_currency(value)
    return normalized


def parse_boolean(value: Any) -> Tuple[bool, bool]:
    if isinstance(value, bool):
        return value, True

    if isinstance(value, int) and value in (0, 1):
        return bool(value), True

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {"true", "1", "yes", "on"}:
            return True, True

        if normalized in {"false", "0", "no", "off"}:
            return False, True

    return False, False


def normalize_renter_type(renter_type: Any) -> Tuple[str, bool]:
    normalized = str(renter_type or "").strip().lower()
    valid_types = {member.value for member in RenterType}

    if normalized not in valid_types:
        return RenterType.WORKER.value, False

    return normalized, True


def normalize_area_demand(area_demand: Any) -> Tuple[str, bool, bool]:
    provided = area_demand is not None and str(area_demand).strip() != ""

    if not provided:
        return DemandLevel.MEDIUM.value, False, False

    normalized = str(area_demand).strip().upper()
    valid_levels = {member.value for member in DemandLevel}

    if normalized not in valid_levels:
        return DemandLevel.MEDIUM.value, True, False

    return normalized, True, True


def normalize_document_set(documents: Optional[List[str]]) -> Set[str]:
    return {
        canonicalize_document(document)
        for document in documents or []
        if normalize_document_text(document)
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
    normalized_renter_type, renter_type_was_valid = normalize_renter_type(
        renter_type
    )
    normalized_area_demand, demand_was_provided, demand_was_valid = (
        normalize_area_demand(area_demand)
    )

    normalized_income, income_was_valid = parse_currency(monthly_income)
    normalized_rent, rent_was_valid = parse_currency(monthly_rent)
    normalized_deposit, deposit_was_valid = parse_currency(security_deposit)
    normalized_fee, fee_was_valid = parse_currency(application_fee)
    normalized_guarantor_income, guarantor_income_was_valid = parse_currency(
        guarantor_monthly_income
    )
    normalized_bursary_flag, bursary_flag_was_valid = parse_boolean(
        is_bursary_student
    )

    return EvaluationInput(
        renter_type=normalized_renter_type,
        monthly_income=normalized_income,
        submitted_documents=normalize_document_set(submitted_documents),
        monthly_rent=normalized_rent,
        security_deposit=normalized_deposit,
        application_fee=normalized_fee,
        required_documents=normalize_document_set(required_documents),
        area_demand=normalized_area_demand,
        guarantor_monthly_income=normalized_guarantor_income,
        is_bursary_student=normalized_bursary_flag,
        renter_type_was_valid=renter_type_was_valid,
        area_demand_was_provided=demand_was_provided,
        area_demand_was_valid=demand_was_valid,
        monthly_income_was_valid=income_was_valid,
        monthly_rent_was_valid=rent_was_valid,
        security_deposit_was_valid=deposit_was_valid,
        application_fee_was_valid=fee_was_valid,
        guarantor_income_was_valid=guarantor_income_was_valid,
        bursary_flag_was_valid=bursary_flag_was_valid,
    )


def format_currency_zar(value: int) -> str:
    value = normalize_currency(value)
    return f"{CURRENCY_SYMBOL}{value:,}".replace(",", " ")


def calculate_budget_bands(monthly_income: int) -> Dict[str, int]:
    """Budget guidance uses the renter's own declared income/support only."""
    monthly_income = normalize_currency(monthly_income)

    return {
        "conservative": int(monthly_income * 0.25),
        "recommended": int(monthly_income * RECOMMENDED_RENT_TO_INCOME_CAP),
        "upper_limit": int(monthly_income * UPPER_RENT_TO_INCOME_CAP),
    }


def calculate_ratio_percentage(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 999.0

    return (numerator / denominator) * 100.0


def clamp_score(score: int) -> int:
    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def deduplicate_preserve_order(items: List[str]) -> List[str]:
    return list(dict.fromkeys(items))


def contains_text(items: List[str], text: str) -> bool:
    target = normalize_document_text(text)
    return any(normalize_document_text(item) == target for item in items)


def add_reason(reasons: List[str], message: str) -> None:
    if not contains_text(reasons, message):
        reasons.append(message)


def add_priority_reason(reasons: List[str], message: str) -> None:
    if not contains_text(reasons, message):
        reasons.insert(0, message)


def add_action(actions: List[str], message: str) -> None:
    if not contains_text(actions, message):
        actions.append(message)


def add_priority_action(actions: List[str], message: str) -> None:
    if not contains_text(actions, message):
        actions.insert(0, message)


def trim_output_lists(
    reasons: List[str],
    actions: List[str],
) -> Tuple[List[str], List[str]]:
    return (
        deduplicate_preserve_order(reasons)[:6],
        deduplicate_preserve_order(actions)[:5],
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
    """Apply to the raw score. Final clamping happens once at the end."""
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


# ---------------------------------------------------------------------------
# Document rules
# ---------------------------------------------------------------------------


def document_matches(required_document: str, submitted_document: str) -> bool:
    """Use exact canonical equality; never use unrestricted substring matching."""
    return canonicalize_document(required_document) == canonicalize_document(
        submitted_document
    )


def find_missing_documents(
    required_documents: Set[str],
    submitted_documents: Set[str],
) -> Set[str]:
    return {
        required_document
        for required_document in required_documents
        if required_document not in submitted_documents
    }


def has_document(
    submitted_documents: Set[str],
    required_document: str,
) -> bool:
    return canonicalize_document(required_document) in submitted_documents


def find_missing_document_groups(
    required_document_groups: List[List[str]],
    submitted_documents: Set[str],
) -> List[List[str]]:
    missing_groups: List[List[str]] = []

    for group in required_document_groups:
        if not any(
            has_document(submitted_documents, document) for document in group
        ):
            missing_groups.append(group)

    return missing_groups


def format_missing_document_groups(
    missing_groups: List[List[str]],
) -> str:
    formatted_groups = [
        group[0] if len(group) == 1 else " or ".join(group)
        for group in missing_groups
    ]
    return ", ".join(formatted_groups)


def canonical_documents_from_groups(
    groups: List[List[str]],
) -> Set[str]:
    return {
        canonicalize_document(document)
        for group in groups
        for document in group
    }


def has_complete_guarantor_documents(
    submitted_documents: Set[str],
) -> bool:
    return all(
        has_document(submitted_documents, document)
        for document in (
            "guarantor letter",
            "guarantor payslip",
            "guarantor bank statement",
        )
    )


def has_valid_guarantor_support(inputs: EvaluationInput) -> bool:
    return (
        inputs.guarantor_income_was_valid
        and inputs.guarantor_monthly_income > 0
        and has_complete_guarantor_documents(inputs.submitted_documents)
    )


def has_bursary_proof(submitted_documents: Set[str]) -> bool:
    return any(
        has_document(submitted_documents, document)
        for document in (
            "bursary award letter",
            "nsfas award letter",
            "bursary confirmation",
        )
    )


def has_relevant_submitted_document(inputs: EvaluationInput) -> bool:
    expected_documents = canonical_documents_from_groups(
        REQUIRED_DOCUMENT_CLUSTERS.get(inputs.renter_type, [])
    )
    relevant_documents = expected_documents | inputs.required_documents

    if inputs.is_student:
        relevant_documents |= {
            canonicalize_document("bursary award letter"),
            canonicalize_document("nsfas award letter"),
            canonicalize_document("guarantor letter"),
            canonicalize_document("guarantor payslip"),
            canonicalize_document("guarantor bank statement"),
        }

    return bool(inputs.submitted_documents & relevant_documents)


# ---------------------------------------------------------------------------
# Evaluation rules
# ---------------------------------------------------------------------------


def evaluate_input_quality(
    score: int,
    inputs: EvaluationInput,
    reasons: List[str],
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> Tuple[int, bool]:
    """Return the score and whether affordability should be skipped."""
    skip_affordability = False

    if not inputs.renter_type_was_valid:
        add_reason(
            reasons,
            "The renter type was not recognised, so the worker pathway was used as a fallback.",
        )
        add_action(
            actions,
            "Choose worker, new professional, or student so the correct document rules are applied.",
        )

    if not inputs.area_demand_was_valid:
        add_reason(
            reasons,
            "The area-demand value was missing or invalid, so medium demand was used as a fallback.",
        )
        add_action(
            actions,
            "Confirm whether demand for the area is low, medium, or high.",
        )

    if inputs.is_student and not inputs.bursary_flag_was_valid:
        add_reason(
            reasons,
            "The bursary-status value was invalid, so the non-bursary student pathway was used.",
        )
        add_action(
            actions,
            "Confirm whether the student has verified bursary or NSFAS funding.",
        )

    if not inputs.monthly_income_was_valid:
        add_reason(
            reasons,
            "The monthly income or support value was missing or invalid.",
        )

    if not inputs.monthly_rent_was_valid or inputs.monthly_rent <= 0:
        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Missing monthly rent",
            score_delta=-MISSING_RENT_PENALTY,
        )
        add_priority_reason(
            reasons,
            "A valid monthly rent was not provided, so the listing cannot be assessed reliably.",
        )
        add_priority_action(
            actions,
            "Add the listing's monthly rent before relying on this recommendation.",
        )
        skip_affordability = True

    if not inputs.security_deposit_was_valid:
        add_reason(
            reasons,
            "The security deposit was not confirmed, so the upfront-cost estimate may be incomplete.",
        )
        add_action(
            actions,
            "Confirm the deposit before deciding whether the total upfront cost is manageable.",
        )

    if not inputs.application_fee_was_valid:
        add_reason(
            reasons,
            "The application fee was not confirmed, so the upfront-cost estimate may be incomplete.",
        )

    return score, skip_affordability


def evaluate_non_bursary_student_guarantor(
    score: int,
    qualifying_income: int,
    inputs: EvaluationInput,
    reasons: List[str],
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> Tuple[int, int]:
    if has_valid_guarantor_support(inputs):
        qualifying_income = max(
            inputs.monthly_income,
            inputs.guarantor_monthly_income,
        )
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
            "The application includes guarantor income and a complete guarantor document pack.",
        )
        add_action(
            actions,
            "Make sure the guarantor documents are recent and match the guarantor's name.",
        )
        return score, qualifying_income

    if inputs.monthly_income_was_valid and inputs.monthly_income > 0:
        add_reason(
            reasons,
            "No complete guarantor file was provided, so affordability is assessed using the student's own declared monthly income or support.",
        )
        return score, qualifying_income

    score = apply_score_adjustment(
        current_score=score,
        score_breakdown=score_breakdown,
        title="Missing guarantor support",
        score_delta=-45,
    )
    add_priority_reason(
        reasons,
        "The student has no qualifying monthly income or complete guarantor support.",
    )
    add_action(
        actions,
        "Add guarantor income, a guarantor letter, a guarantor payslip, and guarantor bank statements before applying.",
    )
    return score, qualifying_income


def evaluate_bursary_student(
    score: int,
    qualifying_income: int,
    inputs: EvaluationInput,
    reasons: List[str],
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> Tuple[int, int, bool]:
    clear_bursary_proof = has_bursary_proof(inputs.submitted_documents)
    valid_guarantor = has_valid_guarantor_support(inputs)

    if not clear_bursary_proof:
        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Missing bursary confirmation",
            score_delta=-35,
        )
        add_priority_reason(
            reasons,
            "The applicant was marked as bursary-funded, but no bursary, NSFAS, or funding confirmation was provided.",
        )
        add_action(
            actions,
            "Attach an official bursary, NSFAS, or funding confirmation before applying.",
        )

        if valid_guarantor:
            qualifying_income = max(
                qualifying_income,
                inputs.guarantor_monthly_income,
            )
            score = apply_score_adjustment(
                current_score=score,
                score_breakdown=score_breakdown,
                title="Guarantor fallback support",
                score_delta=10,
                details=(
                    "Guarantor income: "
                    f"{format_currency_zar(inputs.guarantor_monthly_income)}"
                ),
            )
            add_reason(
                reasons,
                "A complete guarantor file provides fallback support while bursary evidence is missing.",
            )

        # Without verified bursary proof, use the normal affordability path.
        return score, qualifying_income, False

    monthly_shortfall = max(0, inputs.monthly_rent - inputs.monthly_income)

    if monthly_shortfall == 0:
        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Bursary fully covers rent",
            score_delta=20,
        )
        add_reason(
            reasons,
            "Verified funding appears to cover the full monthly rent.",
        )
        add_action(
            actions,
            "Include the full funding letter and proof of registration so the landlord can verify the funding quickly.",
        )
        return score, qualifying_income, True

    coverage_ratio = (
        inputs.monthly_income / inputs.monthly_rent
        if inputs.monthly_rent > 0
        else 0.0
    )

    if valid_guarantor:
        qualifying_income = max(
            qualifying_income,
            inputs.guarantor_monthly_income,
        )
        penalty = 15
        title = "Bursary shortfall with guarantor backup"
        add_reason(
            reasons,
            "Funding does not fully cover the rent, but a complete guarantor file provides additional application support.",
        )
        add_action(
            actions,
            "Confirm with the landlord that the guarantor is accepted for the funding shortfall.",
        )
    else:
        # A larger uncovered proportion creates a larger penalty.
        shortfall_ratio = 1.0 - max(0.0, min(1.0, coverage_ratio))
        penalty = max(20, math.ceil(55 * shortfall_ratio))
        title = "Bursary funding shortfall"
        add_priority_reason(
            reasons,
            "Verified funding does not fully cover the monthly rent and no complete guarantor backup was provided.",
        )
        add_action(
            actions,
            "Choose a listing covered by the funding or add a complete guarantor file before applying.",
        )

    score = apply_score_adjustment(
        current_score=score,
        score_breakdown=score_breakdown,
        title=title,
        score_delta=-penalty,
        details=(
            f"Monthly shortfall: {format_currency_zar(monthly_shortfall)}; "
            f"coverage: {coverage_ratio * 100:.0f}%"
        ),
    )

    # Funding coverage is assessed directly, so a salary-style ratio is skipped.
    return score, qualifying_income, True


def evaluate_affordability(
    score: int,
    monthly_rent: int,
    qualifying_income: int,
    reasons: List[str],
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> int:
    if qualifying_income <= 0:
        add_priority_reason(
            reasons,
            "No qualifying monthly income or support was provided, so affordability cannot be verified.",
        )
        add_action(
            actions,
            "Add monthly income, regular support, guarantor income, or verified funding before applying.",
        )
        return apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Missing income information",
            score_delta=-70,
        )

    rent_to_income_ratio = monthly_rent / qualifying_income

    if rent_to_income_ratio <= RECOMMENDED_RENT_TO_INCOME_CAP:
        add_reason(
            reasons,
            "The rent is within a healthy affordability range for the monthly income or support provided.",
        )
        add_action(
            actions,
            "Keep recent evidence showing that the declared monthly income or support is regular and available.",
        )
        return score

    risk_range = (
        EXTREME_RENT_TO_INCOME_CAP - RECOMMENDED_RENT_TO_INCOME_CAP
    )
    excess_ratio = (
        min(rent_to_income_ratio, EXTREME_RENT_TO_INCOME_CAP)
        - RECOMMENDED_RENT_TO_INCOME_CAP
    )
    proportional_penalty = max(
        1,
        math.ceil(
            (excess_ratio / risk_range) * MAX_AFFORDABILITY_PENALTY
        ),
    )

    score = apply_score_adjustment(
        current_score=score,
        score_breakdown=score_breakdown,
        title="Affordability risk",
        score_delta=-proportional_penalty,
        details=f"{rent_to_income_ratio * 100:.0f}% rent-to-income ratio",
    )

    if rent_to_income_ratio >= EXTREME_RENT_TO_INCOME_CAP:
        add_priority_reason(
            reasons,
            "The rent is very high compared with the monthly income or support provided.",
        )
        add_action(
            actions,
            "Look for a lower-rent listing or provide stronger verified support.",
        )
    elif rent_to_income_ratio > UPPER_RENT_TO_INCOME_CAP:
        add_reason(
            reasons,
            "The rent is above the safer affordability range and may concern landlords or agents.",
        )
        add_action(
            actions,
            "Consider listings closer to the recommended rent range or strengthen the application with verified support.",
        )
    else:
        add_reason(
            reasons,
            "The rent is slightly above the recommended affordability range.",
        )
        add_action(
            actions,
            "Apply only if the supporting documents show that the rent remains manageable.",
        )

    return score


def evaluate_renter_type_documents(
    score: int,
    inputs: EvaluationInput,
    reasons: List[str],
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> Tuple[int, Set[str]]:
    expected_groups = REQUIRED_DOCUMENT_CLUSTERS.get(inputs.renter_type, [])
    missing_groups = find_missing_document_groups(
        expected_groups,
        inputs.submitted_documents,
    )

    if not missing_groups:
        add_reason(
            reasons,
            "The core supporting documents match what is usually expected for this renter type.",
        )
        return score, set()

    missing_text = format_missing_document_groups(missing_groups)
    missing_canonical = canonical_documents_from_groups(missing_groups)
    penalty = min(
        MAX_PROFILE_DOCUMENT_PENALTY,
        PROFILE_DOCUMENT_PENALTY_PER_GROUP * len(missing_groups),
    )

    score = apply_score_adjustment(
        current_score=score,
        score_breakdown=score_breakdown,
        title="Missing renter profile documents",
        score_delta=-penalty,
        details=missing_text,
    )
    add_reason(
        reasons,
        f"Standard renter documents are missing: {missing_text}.",
    )
    add_action(
        actions,
        f"Prepare these standard documents before applying: {missing_text}.",
    )
    return score, missing_canonical


def evaluate_required_documents(
    score: int,
    required_documents: Set[str],
    submitted_documents: Set[str],
    profile_missing_documents: Set[str],
    reasons: List[str],
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> int:
    if not required_documents:
        add_reason(
            reasons,
            "No listing-specific document requirements were entered.",
        )
        add_action(
            actions,
            "Check the listing and confirm every required document before applying.",
        )
        return score

    missing_documents = find_missing_documents(
        required_documents,
        submitted_documents,
    )

    if not missing_documents:
        add_reason(
            reasons,
            "The submitted documents appear to cover the listing requirements.",
        )
        return score

    overlapping = missing_documents & profile_missing_documents
    newly_missing = missing_documents - profile_missing_documents
    penalty = min(
        MAX_REQUIRED_DOCUMENT_PENALTY,
        (
            REQUIRED_DOCUMENT_PENALTY_PER_DOCUMENT * len(newly_missing)
            + OVERLAPPING_REQUIRED_DOCUMENT_PENALTY * len(overlapping)
        ),
    )
    penalty = max(1, penalty)
    missing_text = ", ".join(sorted(missing_documents))

    score = apply_score_adjustment(
        current_score=score,
        score_breakdown=score_breakdown,
        title="Missing required documents",
        score_delta=-penalty,
        details=missing_text,
    )
    add_reason(
        reasons,
        f"The listing asks for documents that are not currently covered: {missing_text}.",
    )
    add_action(
        actions,
        f"Do not apply yet unless you can add: {missing_text}.",
    )
    return score


def evaluate_area_demand(
    score: int,
    area_demand: str,
    reasons: List[str],
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> int:
    if area_demand == DemandLevel.HIGH.value:
        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="High-demand rental area",
            score_delta=-10,
        )
        add_reason(
            reasons,
            "The listing is in a high-demand area, so competition may be stronger.",
        )
        add_action(
            actions,
            "Apply quickly with a complete document pack.",
        )
    elif area_demand == DemandLevel.LOW.value:
        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Lower competition rental area",
            score_delta=5,
        )
        add_reason(
            reasons,
            "Lower area demand may improve the application's chances.",
        )
    else:
        add_reason(
            reasons,
            "Area demand is moderate, so affordability and documents remain the main factors.",
        )

    return score


def evaluate_upfront_costs(
    score: int,
    upfront_income_basis: int,
    inputs: EvaluationInput,
    reasons: List[str],
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> int:
    if upfront_income_basis <= 0:
        return score

    if not (
        inputs.monthly_rent_was_valid
        and inputs.security_deposit_was_valid
        and inputs.application_fee_was_valid
    ):
        return score

    total_upfront_cost = (
        inputs.monthly_rent
        + inputs.security_deposit
        + inputs.application_fee
    )
    upfront_ratio = total_upfront_cost / upfront_income_basis

    if upfront_ratio >= SEVERE_UPFRONT_COST_RATIO:
        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Severe upfront cost pressure",
            score_delta=-SEVERE_UPFRONT_COST_PENALTY,
            details=f"Upfront cost: {format_currency_zar(total_upfront_cost)}",
        )
        add_priority_reason(
            reasons,
            "The upfront cost is extremely high compared with the monthly income or funding provided.",
        )
        add_action(
            actions,
            "Confirm that savings can cover rent, deposit, fees, transport, and essential living costs.",
        )
    elif upfront_ratio >= MODERATE_UPFRONT_COST_RATIO:
        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="High upfront cost pressure",
            score_delta=-MODERATE_UPFRONT_COST_PENALTY,
            details=f"Upfront cost: {format_currency_zar(total_upfront_cost)}",
        )
        add_reason(
            reasons,
            "The upfront cost may be difficult to cover quickly.",
        )
        add_action(
            actions,
            "Ask whether the deposit can be split or consider lower-upfront-cost listings.",
        )
    elif upfront_ratio >= ELEVATED_UPFRONT_COST_RATIO:
        add_reason(
            reasons,
            "The upfront cost is moderately high compared with the monthly income or funding provided.",
        )
        add_action(
            actions,
            "Budget carefully for the first month before committing.",
        )

    return score


# ---------------------------------------------------------------------------
# Final classification
# ---------------------------------------------------------------------------


def determine_verdict(score: int) -> str:
    if score >= 75:
        return ApplicationVerdict.STRONG_MATCH.value
    if score >= 55:
        return ApplicationVerdict.BORDERLINE.value
    return ApplicationVerdict.HIGH_RISK.value


def determine_confidence(inputs: EvaluationInput) -> str:
    confidence_points = 0

    if inputs.monthly_rent_was_valid and inputs.monthly_rent > 0:
        confidence_points += 1

    if inputs.monthly_income_was_valid and inputs.monthly_income > 0:
        confidence_points += 1

    if has_relevant_submitted_document(inputs):
        confidence_points += 1

    if inputs.required_documents:
        confidence_points += 1

    if (
        inputs.area_demand_was_provided
        and inputs.area_demand_was_valid
    ):
        confidence_points += 1

    if inputs.bursary_student and has_bursary_proof(
        inputs.submitted_documents
    ):
        confidence_points += 1

    if inputs.is_student and has_valid_guarantor_support(inputs):
        confidence_points += 1

    if confidence_points >= 5:
        return ConfidenceLevel.HIGH.value
    if confidence_points >= 3:
        return ConfidenceLevel.MEDIUM.value
    return ConfidenceLevel.LOW.value


def build_readable_list(items: List[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def add_verdict_action(
    verdict: str,
    confidence: str,
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> None:
    negative_titles = {
        item["title"]
        for item in score_breakdown
        if int(item.get("delta", 0)) < 0
    }

    if verdict == ApplicationVerdict.STRONG_MATCH.value:
        if confidence == ConfidenceLevel.HIGH.value:
            message = (
                "This looks worth applying for if the listing is legitimate "
                "and the lease terms are acceptable."
            )
        else:
            message = (
                "This appears promising, but confirm the missing listing or "
                "profile information before paying an application fee."
            )
        add_priority_action(actions, message)
        return

    weak_points: List[str] = []

    if negative_titles & {
        "Affordability risk",
        "Missing income information",
        "Bursary funding shortfall",
        "Bursary shortfall with guarantor backup",
        "Missing monthly rent",
    }:
        weak_points.append("affordability")

    if negative_titles & {
        "Missing renter profile documents",
        "Missing required documents",
        "Missing bursary confirmation",
    }:
        weak_points.append("missing documents")

    if negative_titles & {
        "Missing guarantor support",
    }:
        weak_points.append("guarantor support")

    if negative_titles & {
        "High upfront cost pressure",
        "Severe upfront cost pressure",
    }:
        weak_points.append("upfront costs")

    readable = build_readable_list(weak_points)

    if verdict == ApplicationVerdict.BORDERLINE.value:
        message = (
            f"Improve the main weak points before applying: {readable}."
            if weak_points
            else "Review the moderate risk factors before deciding whether to apply."
        )
    else:
        message = (
            f"Consider skipping this listing unless you can resolve: {readable}."
            if weak_points
            else "Consider skipping this listing unless the application can be materially strengthened."
        )

    add_priority_action(actions, message)


# ---------------------------------------------------------------------------
# Public evaluator
# ---------------------------------------------------------------------------


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

    raw_score = 100
    qualifying_income = inputs.monthly_income
    skip_affordability = False

    append_score_breakdown(
        score_breakdown=score_breakdown,
        title="Base match score",
        score_delta=0,
        score_before=raw_score,
        score_after=raw_score,
        details=(
            f"Evaluation configured using {APP_MARKET} rental-market assumptions."
        ),
    )

    raw_score, core_skip = evaluate_input_quality(
        score=raw_score,
        inputs=inputs,
        reasons=reasons,
        actions=actions,
        score_breakdown=score_breakdown,
    )
    skip_affordability = skip_affordability or core_skip

    if inputs.non_bursary_student:
        raw_score, qualifying_income = evaluate_non_bursary_student_guarantor(
            score=raw_score,
            qualifying_income=qualifying_income,
            inputs=inputs,
            reasons=reasons,
            actions=actions,
            score_breakdown=score_breakdown,
        )

    if inputs.bursary_student:
        raw_score, qualifying_income, bursary_skip = evaluate_bursary_student(
            score=raw_score,
            qualifying_income=qualifying_income,
            inputs=inputs,
            reasons=reasons,
            actions=actions,
            score_breakdown=score_breakdown,
        )
        skip_affordability = skip_affordability or bursary_skip

    if not skip_affordability:
        raw_score = evaluate_affordability(
            score=raw_score,
            monthly_rent=inputs.monthly_rent,
            qualifying_income=qualifying_income,
            reasons=reasons,
            actions=actions,
            score_breakdown=score_breakdown,
        )

    raw_score, profile_missing_documents = evaluate_renter_type_documents(
        score=raw_score,
        inputs=inputs,
        reasons=reasons,
        actions=actions,
        score_breakdown=score_breakdown,
    )

    raw_score = evaluate_required_documents(
        score=raw_score,
        required_documents=inputs.required_documents,
        submitted_documents=inputs.submitted_documents,
        profile_missing_documents=profile_missing_documents,
        reasons=reasons,
        actions=actions,
        score_breakdown=score_breakdown,
    )

    raw_score = evaluate_area_demand(
        score=raw_score,
        area_demand=inputs.area_demand,
        reasons=reasons,
        actions=actions,
        score_breakdown=score_breakdown,
    )

    raw_score = evaluate_upfront_costs(
        score=raw_score,
        upfront_income_basis=qualifying_income,
        inputs=inputs,
        reasons=reasons,
        actions=actions,
        score_breakdown=score_breakdown,
    )

    final_score = clamp_score(raw_score)

    if final_score != raw_score:
        append_score_breakdown(
            score_breakdown=score_breakdown,
            title="Score normalisation",
            score_delta=final_score - raw_score,
            score_before=raw_score,
            score_after=final_score,
            details="Final score restricted to the 0-100 range.",
        )

    verdict = determine_verdict(final_score)
    confidence = determine_confidence(inputs)

    add_verdict_action(
        verdict=verdict,
        confidence=confidence,
        actions=actions,
        score_breakdown=score_breakdown,
    )

    append_score_breakdown(
        score_breakdown=score_breakdown,
        title="Final verdict",
        score_delta=0,
        score_before=final_score,
        score_after=final_score,
        details=f"{verdict} ({confidence})",
    )

    reasons, actions = trim_output_lists(reasons, actions)

    return (
        EvaluationResult(
            score=final_score,
            verdict=verdict,
            confidence=confidence,
            reasons=reasons,
            actions=actions,
            breakdown=score_breakdown,
        ),
        calculate_budget_bands(inputs.monthly_income),
    )
