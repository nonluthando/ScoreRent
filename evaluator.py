"""
Cape Town Rental Application Evaluation Engine.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Set, Tuple


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

MODERATE_UPFRONT_COST_PENALTY = 8
SEVERE_UPFRONT_COST_PENALTY = 15


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
    RenterType.STUDENT.value: [
        ["proof of registration", "student id"],
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

    @property
    def is_student(self) -> bool:
        return self.renter_type == RenterType.STUDENT.value

    @property
    def bursary_student(self) -> bool:
        return self.is_student and self.is_bursary_student

    @property
    def non_bursary_student(self) -> bool:
        return self.is_student and not self.is_bursary_student


def normalize_currency(value: Any) -> int:
    try:
        return max(0, int(round(float(value))))
    except (TypeError, ValueError):
        return 0


def format_currency_zar(value: int) -> str:
    value = normalize_currency(value)
    return f"{CURRENCY_SYMBOL}{value:,}".replace(",", " ")


def normalize_renter_type(renter_type: str) -> str:
    renter_type = (renter_type or "").strip().lower()
    valid_types = [member.value for member in RenterType]

    if renter_type not in valid_types:
        return RenterType.WORKER.value

    return renter_type


def normalize_area_demand(area_demand: str) -> str:
    area_demand = (area_demand or DemandLevel.MEDIUM.value).strip().upper()
    valid_levels = [member.value for member in DemandLevel]

    if area_demand not in valid_levels:
        return DemandLevel.MEDIUM.value

    return area_demand


def normalize_document_text(document: str) -> str:
    normalized = str(document or "").strip().lower()

    # Form checkbox values may use snake_case or kebab-case.
    normalized = normalized.replace("_", " ")
    normalized = normalized.replace("-", " ")

    # Collapse repeated whitespace.
    return " ".join(normalized.split())


def normalize_document_set(documents: List[str]) -> Set[str]:
    return {
        normalized_document
        for document in documents or []
        if (normalized_document := normalize_document_text(document))
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
        guarantor_monthly_income=normalize_currency(
            guarantor_monthly_income
        ),
        is_bursary_student=bool(is_bursary_student),
    )


def calculate_budget_bands(monthly_income: int) -> Dict[str, int]:
    monthly_income = normalize_currency(monthly_income)

    return {
        "conservative": int(monthly_income * 0.25),
        "recommended": int(
            monthly_income * RECOMMENDED_RENT_TO_INCOME_CAP
        ),
        "upper_limit": int(monthly_income * UPPER_RENT_TO_INCOME_CAP),
    }


def deduplicate_preserve_order(items: List[str]) -> List[str]:
    return list(dict.fromkeys(items))


def calculate_ratio_percentage(
    numerator: int,
    denominator: int,
) -> float:
    if denominator <= 0:
        return 999.0

    return (numerator / denominator) * 100.0


def contains_text(items: List[str], text: str) -> bool:
    target = normalize_document_text(text)

    return any(
        normalize_document_text(item) == target
        for item in items
    )


def clamp_score(score: int) -> int:
    return max(0, min(100, score))


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
    score_after = clamp_score(current_score + int(score_delta))

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


def add_priority_action(actions: List[str], message: str) -> None:
    if not contains_text(actions, message):
        actions.insert(0, message)


def trim_output_lists(
    reasons: List[str],
    actions: List[str],
) -> Tuple[List[str], List[str]]:
    reasons = deduplicate_preserve_order(reasons)[:6]
    actions = deduplicate_preserve_order(actions)[:5]

    return reasons, actions


def get_document_aliases(document: str) -> List[str]:
    document = normalize_document_text(document)
    aliases = DOCUMENT_ALIASES.get(document, [document])

    return [
        normalize_document_text(alias)
        for alias in aliases
    ]


def document_matches(
    required_document: str,
    submitted_document: str,
) -> bool:
    required_document = normalize_document_text(required_document)
    submitted_document = normalize_document_text(submitted_document)

    required_aliases = get_document_aliases(required_document)
    submitted_aliases = get_document_aliases(submitted_document)

    for required_alias in required_aliases:
        for submitted_alias in submitted_aliases:
            if required_alias == submitted_alias:
                return True

            if required_alias in submitted_alias:
                return True

            if submitted_alias in required_alias:
                return True

    return False


def find_missing_documents(
    required_documents: Set[str],
    submitted_documents: Set[str],
) -> Set[str]:
    missing_documents = set()

    for required_document in required_documents:
        has_match = any(
            document_matches(
                required_document,
                submitted_document,
            )
            for submitted_document in submitted_documents
        )

        if not has_match:
            missing_documents.add(required_document)

    return missing_documents


def has_document(
    submitted_documents: Set[str],
    required_document: str,
) -> bool:
    return any(
        document_matches(
            required_document,
            submitted_document,
        )
        for submitted_document in submitted_documents
    )


def find_missing_document_groups(
    required_document_groups: List[List[str]],
    submitted_documents: Set[str],
) -> List[List[str]]:
    missing_groups = []

    for group in required_document_groups:
        has_group_match = any(
            has_document(submitted_documents, document)
            for document in group
        )

        if not has_group_match:
            missing_groups.append(group)

    return missing_groups


def format_missing_document_groups(
    missing_groups: List[List[str]],
) -> str:
    formatted_groups = []

    for group in missing_groups:
        if len(group) == 1:
            formatted_groups.append(group[0])
        else:
            formatted_groups.append(" or ".join(group))

    return ", ".join(formatted_groups)


def has_complete_guarantor_documents(
    submitted_documents: Set[str],
) -> bool:
    has_guarantor_letter = has_document(
        submitted_documents,
        "guarantor letter",
    )

    has_guarantor_payslip = has_document(
        submitted_documents,
        "guarantor payslip",
    )

    has_guarantor_bank_statement = has_document(
        submitted_documents,
        "guarantor bank statement",
    )

    return all(
        [
            has_guarantor_letter,
            has_guarantor_payslip,
            has_guarantor_bank_statement,
        ]
    )


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

    has_guarantor_income = inputs.guarantor_monthly_income > 0
    own_income_can_be_checked = inputs.monthly_income > 0

    if guarantor_documents_complete and has_guarantor_income:
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
            (
                "Your application is stronger because it includes "
                "guarantor income and supporting guarantor documents."
            ),
        )

        add_action(
            actions,
            (
                "Make sure the guarantor documents are recent, clearly "
                "labelled, and match the guarantor’s name."
            ),
        )

        return score, qualifying_income

    if own_income_can_be_checked:
        add_reason(
            reasons,
            (
                "No complete guarantor file was provided, so affordability "
                "is assessed using your own declared monthly income or "
                "support."
            ),
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
        (
            "As a non-bursary student with no qualifying monthly income "
            "or support, your application is weaker without a complete "
            "guarantor file."
        ),
    )

    add_action(
        actions,
        (
            "Add a guarantor letter, guarantor payslip, guarantor bank "
            "statements, and guarantor income before applying."
        ),
    )

    return score, qualifying_income


def has_bursary_proof(
    submitted_documents: Set[str],
) -> bool:
    return any(
        has_document(submitted_documents, document)
        for document in [
            "bursary award letter",
            "nsfas award letter",
            "bursary confirmation",
        ]
    )


def evaluate_bursary_student(
    score: int,
    inputs: EvaluationInput,
    reasons: List[str],
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> Tuple[int, bool]:
    has_clear_bursary_proof = has_bursary_proof(
        inputs.submitted_documents
    )

    skip_affordability_evaluation = has_clear_bursary_proof

    if not has_clear_bursary_proof:
        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Missing bursary confirmation",
            score_delta=-35,
        )

        add_reason(
            reasons,
            (
                "You marked yourself as a bursary student, but no clear "
                "bursary, NSFAS, or funding confirmation was provided."
            ),
        )

        add_action(
            actions,
            (
                "Attach your bursary award letter, NSFAS confirmation, "
                "or official funding confirmation before applying."
            ),
        )

        return score, skip_affordability_evaluation

    monthly_rent_shortfall = (
        inputs.monthly_rent - inputs.monthly_income
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
            "Your listed funding does not fully cover the monthly rent.",
        )

        add_action(
            actions,
            (
                "Add a guarantor or choose a listing where the rent is "
                "fully covered by your funding."
            ),
        )

        return score, skip_affordability_evaluation

    score = apply_score_adjustment(
        current_score=score,
        score_breakdown=score_breakdown,
        title="Bursary fully covers rent",
        score_delta=20,
    )

    add_reason(
        reasons,
        (
            "Your funding appears to cover the monthly rent, which "
            "strengthens your application."
        ),
    )

    add_action(
        actions,
        (
            "Include the full funding letter and proof of registration "
            "so the landlord can verify your student funding quickly."
        ),
    )

    return score, skip_affordability_evaluation


def evaluate_affordability(
    score: int,
    monthly_rent: int,
    qualifying_income: int,
    reasons: List[str],
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> int:
    if qualifying_income <= 0:
        add_reason(
            reasons,
            (
                "No qualifying monthly income or support was provided, "
                "so affordability cannot be verified."
            ),
        )

        add_action(
            actions,
            (
                "Add monthly income, regular monthly support, guarantor "
                "income, or funding proof before applying."
            ),
        )

        return apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Missing income information",
            score_delta=-70,
        )

    rent_to_income_ratio = (
        calculate_ratio_percentage(
            monthly_rent,
            qualifying_income,
        )
        / 100.0
    )

    if rent_to_income_ratio <= RECOMMENDED_RENT_TO_INCOME_CAP:
        add_reason(
            reasons,
            (
                "The rent is within a healthy affordability range for "
                "the monthly income or support provided."
            ),
        )

        add_action(
            actions,
            (
                "Keep bank statements or other proof showing that the "
                "declared monthly income or support is regular and "
                "available."
            ),
        )

        return score

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

    if rent_to_income_ratio >= EXTREME_RENT_TO_INCOME_CAP:
        add_reason(
            reasons,
            (
                "The rent is very high compared with the monthly income "
                "or support provided, which may reduce approval chances."
            ),
        )

        add_action(
            actions,
            (
                "Look for a lower-rent listing, add reliable monthly "
                "support or a guarantor, or provide stronger evidence "
                "of stable funds."
            ),
        )

    elif rent_to_income_ratio > UPPER_RENT_TO_INCOME_CAP:
        add_reason(
            reasons,
            (
                "The rent is above the safer affordability range and "
                "may concern landlords or agents."
            ),
        )

        add_action(
            actions,
            (
                "Consider listings closer to your recommended rent "
                "range or strengthen the application with additional "
                "verified support."
            ),
        )

    else:
        add_reason(
            reasons,
            (
                "The rent is slightly above the recommended "
                "affordability range."
            ),
        )

        add_action(
            actions,
            (
                "Apply only if your supporting documents clearly show "
                "that the monthly income or support is stable and the "
                "rent is manageable."
            ),
        )

    return score


def evaluate_renter_type_documents(
    score: int,
    inputs: EvaluationInput,
    reasons: List[str],
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> int:
    expected_document_groups = REQUIRED_DOCUMENT_CLUSTERS.get(
        inputs.renter_type,
        [],
    )

    missing_groups = find_missing_document_groups(
        required_document_groups=expected_document_groups,
        submitted_documents=inputs.submitted_documents,
    )

    if not missing_groups:
        add_reason(
            reasons,
            (
                "Your core supporting documents match what is usually "
                "expected for this renter type."
            ),
        )

        return score

    missing_documents_text = format_missing_document_groups(
        missing_groups
    )

    score = apply_score_adjustment(
        current_score=score,
        score_breakdown=score_breakdown,
        title="Missing renter profile documents",
        score_delta=-15,
        details=missing_documents_text,
    )

    add_reason(
        reasons,
        (
            "Your application may be weaker because these standard "
            f"documents are missing: {missing_documents_text}."
        ),
    )

    add_action(
        actions,
        (
            "Prepare these standard documents before applying: "
            f"{missing_documents_text}."
        ),
    )

    return score


def evaluate_required_documents(
    score: int,
    required_documents: Set[str],
    submitted_documents: Set[str],
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
            (
                "Check the listing carefully and add any required "
                "documents before submitting an application."
            ),
        )

        return score

    missing_required_documents = find_missing_documents(
        required_documents=required_documents,
        submitted_documents=submitted_documents,
    )

    if not missing_required_documents:
        add_reason(
            reasons,
            "You appear to have the documents requested by the listing.",
        )

        return score

    missing_documents_text = ", ".join(
        sorted(missing_required_documents)
    )

    score = apply_score_adjustment(
        current_score=score,
        score_breakdown=score_breakdown,
        title="Missing required documents",
        score_delta=-20,
        details=missing_documents_text,
    )

    add_reason(
        reasons,
        (
            "The listing asks for documents that are not currently "
            f"covered: {missing_documents_text}."
        ),
    )

    add_action(
        actions,
        (
            "Do not apply yet unless you can add: "
            f"{missing_documents_text}."
        ),
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
            (
                "This is marked as a high-demand area, so competition "
                "may be stronger."
            ),
        )

        add_action(
            actions,
            (
                "Apply quickly with a complete document pack and avoid "
                "sending an incomplete application."
            ),
        )

        return score

    if area_demand == DemandLevel.LOW.value:
        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Lower competition rental area",
            score_delta=5,
        )

        add_reason(
            reasons,
            (
                "Lower area demand may improve your chances compared "
                "with more competitive listings."
            ),
        )

        add_action(
            actions,
            (
                "Use this advantage by applying early and keeping your "
                "documents complete."
            ),
        )

        return score

    add_reason(
        reasons,
        (
            "Area demand is moderate, so application strength will "
            "mostly depend on affordability and documents."
        ),
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

    total_upfront_cost = (
        inputs.monthly_rent
        + inputs.security_deposit
        + inputs.application_fee
    )

    upfront_cost_ratio = (
        total_upfront_cost / upfront_income_basis
    )

    if upfront_cost_ratio > SEVERE_UPFRONT_COST_RATIO:
        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="Severe upfront cost pressure",
            score_delta=-SEVERE_UPFRONT_COST_PENALTY,
            details=(
                "Upfront cost: "
                f"{format_currency_zar(total_upfront_cost)}"
            ),
        )

        add_reason(
            reasons,
            (
                "The upfront cost is extremely high compared with the "
                "monthly income or funding provided."
            ),
        )

        add_action(
            actions,
            (
                "Confirm you have enough savings for rent, deposit, "
                "fees, transport, and basic living costs before "
                "applying."
            ),
        )

    elif upfront_cost_ratio > MODERATE_UPFRONT_COST_RATIO:
        score = apply_score_adjustment(
            current_score=score,
            score_breakdown=score_breakdown,
            title="High upfront cost pressure",
            score_delta=-MODERATE_UPFRONT_COST_PENALTY,
            details=(
                "Upfront cost: "
                f"{format_currency_zar(total_upfront_cost)}"
            ),
        )

        add_reason(
            reasons,
            "The upfront cost may be difficult to cover quickly.",
        )

        add_action(
            actions,
            (
                "Ask whether the deposit can be split or consider "
                "listings with lower upfront costs."
            ),
        )

    elif upfront_cost_ratio > ELEVATED_UPFRONT_COST_RATIO:
        add_reason(
            reasons,
            (
                "The upfront cost is moderately high compared with the "
                "monthly income or funding provided."
            ),
        )

        add_action(
            actions,
            (
                "Budget for the first month carefully before committing "
                "to the application."
            ),
        )

    return score


def determine_verdict(score: int) -> str:
    if score >= 75:
        return ApplicationVerdict.STRONG_MATCH.value

    if score >= 55:
        return ApplicationVerdict.BORDERLINE.value

    return ApplicationVerdict.HIGH_RISK.value


def determine_confidence(inputs: EvaluationInput) -> str:
    confidence_points = 0

    if inputs.monthly_rent > 0:
        confidence_points += 1

    if inputs.monthly_income > 0:
        confidence_points += 1

    if inputs.submitted_documents:
        confidence_points += 1

    if inputs.required_documents:
        confidence_points += 1

    if inputs.area_demand in [
        DemandLevel.LOW.value,
        DemandLevel.MEDIUM.value,
        DemandLevel.HIGH.value,
    ]:
        confidence_points += 1

    if inputs.is_student:
        if (
            inputs.bursary_student
            and has_bursary_proof(inputs.submitted_documents)
        ):
            confidence_points += 1

        if inputs.non_bursary_student and (
            inputs.monthly_income > 0
            or inputs.guarantor_monthly_income > 0
        ):
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
    actions: List[str],
    score_breakdown: List[Dict[str, Any]],
) -> None:
    negative_breakdown_titles = {
        item["title"]
        for item in score_breakdown
        if int(item.get("delta", 0)) < 0
    }

    if verdict == ApplicationVerdict.STRONG_MATCH.value:
        add_priority_action(
            actions,
            (
                "This looks worth applying for if the listing is "
                "legitimate and the lease terms are acceptable."
            ),
        )
        return

    weak_points: List[str] = []

    affordability_titles = {
        "Affordability risk",
        "Missing income information",
        "Bursary funding shortfall",
    }

    document_titles = {
        "Missing renter profile documents",
        "Missing required documents",
        "Missing bursary confirmation",
    }

    upfront_cost_titles = {
        "High upfront cost pressure",
        "Severe upfront cost pressure",
    }

    if negative_breakdown_titles & affordability_titles:
        weak_points.append("affordability")

    if negative_breakdown_titles & document_titles:
        weak_points.append("missing documents")

    if "Missing guarantor support" in negative_breakdown_titles:
        weak_points.append("guarantor support")

    if negative_breakdown_titles & upfront_cost_titles:
        weak_points.append("upfront costs")

    readable_weak_points = build_readable_list(weak_points)

    if verdict == ApplicationVerdict.BORDERLINE.value:
        if weak_points:
            add_priority_action(
                actions,
                (
                    "Improve the main weak "
                    f"{'point' if len(weak_points) == 1 else 'points'} "
                    f"before applying: {readable_weak_points}."
                ),
            )
        else:
            add_priority_action(
                actions,
                (
                    "Review the moderate risk factors identified below "
                    "before deciding whether to apply."
                ),
            )

        return

    if weak_points:
        add_priority_action(
            actions,
            (
                "Consider skipping this listing unless you can resolve "
                f"the main issues: {readable_weak_points}."
            ),
        )
    else:
        add_priority_action(
            actions,
            (
                "Consider skipping this listing unless you can "
                "materially strengthen the application."
            ),
        )


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
            f"Evaluation calibrated for the {APP_MARKET} "
            "rental market."
        ),
    )

    if inputs.non_bursary_student:
        score, qualifying_income = (
            evaluate_non_bursary_student_guarantor(
                score=score,
                qualifying_income=qualifying_income,
                inputs=inputs,
                reasons=reasons,
                actions=actions,
                score_breakdown=score_breakdown,
            )
        )

    if inputs.bursary_student:
        score, skip_affordability_evaluation = (
            evaluate_bursary_student(
                score=score,
                inputs=inputs,
                reasons=reasons,
                actions=actions,
                score_breakdown=score_breakdown,
            )
        )

    if not skip_affordability_evaluation:
        score = evaluate_affordability(
            score=score,
            monthly_rent=inputs.monthly_rent,
            qualifying_income=qualifying_income,
            reasons=reasons,
            actions=actions,
            score_breakdown=score_breakdown,
        )

    score = evaluate_renter_type_documents(
        score=score,
        inputs=inputs,
        reasons=reasons,
        actions=actions,
        score_breakdown=score_breakdown,
    )

    score = evaluate_required_documents(
        score=score,
        required_documents=inputs.required_documents,
        submitted_documents=inputs.submitted_documents,
        reasons=reasons,
        actions=actions,
        score_breakdown=score_breakdown,
    )

    score = evaluate_area_demand(
        score=score,
        area_demand=inputs.area_demand,
        reasons=reasons,
        actions=actions,
        score_breakdown=score_breakdown,
    )

    score = evaluate_upfront_costs(
        score=score,
        upfront_income_basis=qualifying_income,
        inputs=inputs,
        reasons=reasons,
        actions=actions,
        score_breakdown=score_breakdown,
    )

    score = clamp_score(score)
    verdict = determine_verdict(score)
    confidence = determine_confidence(inputs)

    add_verdict_action(
        verdict=verdict,
        actions=actions,
        score_breakdown=score_breakdown,
    )

    append_score_breakdown(
        score_breakdown=score_breakdown,
        title="Final verdict",
        score_delta=0,
        score_before=score,
        score_after=score,
        details=f"{verdict} ({confidence})",
    )

    reasons, actions = trim_output_lists(
        reasons=reasons,
        actions=actions,
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
