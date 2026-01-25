import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class EvaluationResult:
    score: int
    verdict: str
    confidence: str
    reasons: List[str]
    actions: List[str]
    breakdown: List[Dict[str, Any]]


VERDICTS = ["WORTH_APPLYING", "BORDERLINE", "NOT_WORTH_IT"]
RENTER_TYPES = ["worker", "new_professional", "student"]

DOC_CLUSTERS = {
    "worker": {"bank_statement", "payslip"},
    "new_professional": {"employment_contract", "guarantor_letter"},
    "student": {"proof_of_registration", "bursary_letter", "guarantor_letter"},
}

DEMAND_LEVELS = ["LOW", "MEDIUM", "HIGH"]


def suggested_budget_bands(monthly_income: int) -> Dict[str, int]:
    return {
        "conservative": int(monthly_income * 0.25),
        "recommended": int(monthly_income * 0.30),
        "upper_limit": int(monthly_income * 0.35),
    }


def _dedupe_keep_order(items: List[str]) -> List[str]:
    return list(dict.fromkeys(items))


def _push_breakdown(
    breakdown: List[Dict[str, Any]],
    title: str,
    delta: int,
    before: int,
    after: int,
    details: str = "",
):
    breakdown.append(
        {
            "title": title,
            "delta": delta,
            "before": before,
            "after": after,
            "details": details,
        }
    )


def _apply(
    score: int,
    breakdown: List[Dict[str, Any]],
    title: str,
    delta: int,
    details: str = "",
) -> int:
    before = score
    after = score + delta
    _push_breakdown(breakdown, title, delta, before, after, details=details)
    return after


def _format_currency(value: int) -> str:
    return f"R{int(value):,}".replace(",", " ")


def evaluate(
    renter_type: str,
    monthly_income: int,
    renter_docs: List[str],
    rent: int,
    deposit: int,
    application_fee: int,
    required_documents: List[str],
    area_demand: str,
    guarantor_monthly_income: int = 0,
    is_bursary_student: bool = False,
) -> Tuple[EvaluationResult, Dict[str, int]]:
    reasons: List[str] = []
    actions: List[str] = []
    breakdown: List[Dict[str, Any]] = []

    score = 70
    _push_breakdown(
        breakdown,
        "Base score",
        0,
        0,
        score,
        "Score starts at 70 and is adjusted by affordability, documents, and demand.",
    )

    renter_type = (renter_type or "").strip().lower()
    renter_docs_set = set(d.strip().lower() for d in (renter_docs or []) if d and d.strip())
    required_docs_set = set(d.strip().lower() for d in (required_documents or []) if d and d.strip())
    area_demand = (area_demand or "MEDIUM").upper().strip()

    if renter_type not in RENTER_TYPES:
        renter_type = "worker"

    if area_demand not in DEMAND_LEVELS:
        area_demand = "MEDIUM"

    is_student = renter_type == "student"
    bursary_student = is_student and (
        bool(is_bursary_student) or ("bursary_letter" in renter_docs_set)
    )
    non_bursary_student = is_student and not bursary_student

    has_employment_contract = "employment_contract" in renter_docs_set
    has_guarantor_letter = "guarantor_letter" in renter_docs_set

    effective_income_for_affordability = monthly_income
    if non_bursary_student and guarantor_monthly_income > 0:
        effective_income_for_affordability = guarantor_monthly_income

    bands = suggested_budget_bands(int(effective_income_for_affordability))
    upper_limit = bands["upper_limit"]
    recommended = bands["recommended"]

    if is_student:
        if "proof_of_registration" not in renter_docs_set:
            score = _apply(score, breakdown, "Missing proof of registration", -25)
            reasons.append("Student applicants must provide proof of registration.")
            actions.append("Upload proof of registration.")

        if bursary_student:
            reasons.append("Bursary student selected (financial support assumed).")

            if monthly_income >= rent:
                score = _apply(score, breakdown, "Bursary/support covers rent", +15)
                reasons.append("Bursary/financial support covers the rent.")
                actions.append("Apply — affordability looks strong for your situation.")
        else:
            required_guarantor_docs = {
                "guarantor_letter",
                "guarantor_payslip",
                "guarantor_bank_statement",
            }
            missing = required_guarantor_docs - renter_docs_set
            if missing:
                score = _apply(
                    score,
                    breakdown,
                    "Missing guarantor documentation",
                    -25,
                    details=",
