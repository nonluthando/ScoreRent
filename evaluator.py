import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


# ------------------------------------------------------------
# Market configuration (Cape Town only)
# ------------------------------------------------------------

APP_MARKET = "Cape Town"

CURRENCY_CODE = "ZAR"
CURRENCY_SYMBOL = "R"

# Cape Town calibrated affordability thresholds
CAPE_TOWN_RECOMMENDED_CAP = 0.33
CAPE_TOWN_UPPER_CAP = 0.38
CAPE_TOWN_EXTREME_CAP = 0.45


# ------------------------------------------------------------
# Result object
# ------------------------------------------------------------

@dataclass
class EvaluationResult:
    score: int
    verdict: str
    confidence: str
    reasons: List[str]
    actions: List[str]
    breakdown: List[Dict[str, Any]]




RENTER_TYPES = ["worker", "new_professional", "student"]

DEMAND_LEVELS = ["LOW", "MEDIUM", "HIGH"]

DOC_CLUSTERS = {
    "worker": [
        "bank statement",
        "payslip",
        "employment letter"
    ],
    "new_professional": [
        "employment contract",
        "offer letter",
        "bank statement",
        "guarantor letter"
    ],
    "student": [
        "bursary award letter",
        "nsfas award letter",
        "bursary confirmation",
        "proof of registration",
        "student ID",
        "guarantor letter"
    ],
}


# ------------------------------------------------------------
# Money helpers
# ------------------------------------------------------------

def _money(value: Any) -> int:
    try:
        return max(0, int(round(float(value))))
    except:
        return 0


def _format_currency(value: int) -> str:
    value = _money(value)
    return f"{CURRENCY_SYMBOL}{value:,}".replace(",", " ")


# ------------------------------------------------------------
# Budget bands (Cape Town calibrated)
# ------------------------------------------------------------

def suggested_budget_bands(monthly_income: int) -> Dict[str, int]:

    monthly_income = _money(monthly_income)

    return {
        "conservative": int(monthly_income * 0.25),
        "recommended": int(monthly_income * CAPE_TOWN_RECOMMENDED_CAP),
        "upper_limit": int(monthly_income * CAPE_TOWN_UPPER_CAP),
    }


# ------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------

def _dedupe_keep_order(items: List[str]) -> List[str]:
    return list(dict.fromkeys(items))


def _ratio_pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 999.0
    return (numerator / denominator) * 100.0


def _has_item(items: List[str], text: str) -> bool:
    target = text.strip().lower()
    return any(i.strip().lower() == target for i in items)


def _push_breakdown(
    breakdown: List[Dict[str, Any]],
    title: str,
    delta: int,
    before: int,
    after: int,
    details: str = "",
) -> None:

    breakdown.append(
        {
            "title": title,
            "delta": int(delta),
            "before": int(before),
            "after": int(after),
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
    after = score + int(delta)

    _push_breakdown(
        breakdown,
        title,
        delta,
        before,
        after,
        details,
    )

    return after


def _add_reason(reasons: List[str], text: str) -> None:
    if not _has_item(reasons, text):
        reasons.append(text)


def _add_action(actions: List[str], text: str) -> None:
    if not _has_item(actions, text):
        actions.append(text)


def _trim_output(
    reasons: List[str],
    actions: List[str],
) -> Tuple[List[str], List[str]]:

    reasons = _dedupe_keep_order(reasons)[:5]
    actions = _dedupe_keep_order(actions)[:4]

    return reasons, actions


# ------------------------------------------------------------
# Main evaluator
# ------------------------------------------------------------

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

    # Normalize inputs
    monthly_income = _money(monthly_income)
    rent = _money(rent)
    deposit = _money(deposit)
    application_fee = _money(application_fee)
    guarantor_monthly_income = _money(guarantor_monthly_income)

    reasons: List[str] = []
    actions: List[str] = []
    breakdown: List[Dict[str, Any]] = []

    renter_type = (renter_type or "").strip().lower()
    if renter_type not in RENTER_TYPES:
        renter_type = "worker"

    renter_docs_set = set(d.lower().strip() for d in (renter_docs or []))
    required_docs_set = set(d.lower().strip() for d in (required_documents or []))

    area_demand = (area_demand or "MEDIUM").upper()
    if area_demand not in DEMAND_LEVELS:
        area_demand = "MEDIUM"

    is_student = renter_type == "student"
    bursary_student = is_student and is_bursary_student
    non_bursary_student = is_student and not is_bursary_student

    # Base score
    score = 100

    _push_breakdown(
        breakdown,
        "Base match score",
        0,
        0,
        score,
        f"Evaluation calibrated for {APP_MARKET}",
    )

    # ------------------------------------------------------------
    # Determine effective income
    # ------------------------------------------------------------

    effective_income = monthly_income

    if non_bursary_student:

        has_guarantor_letter = any("guarantor" in d for d in renter_docs_set)
        has_guarantor_payslip = any("guarantor payslip" in d for d in renter_docs_set)
        has_guarantor_bank = any("guarantor bank" in d for d in renter_docs_set)

        guarantor_docs_complete = (
            has_guarantor_letter and
            has_guarantor_payslip and
            has_guarantor_bank
        )

        if guarantor_docs_complete and guarantor_monthly_income > 0:

            effective_income = guarantor_monthly_income

            score = _apply(
                score,
                breakdown,
                "Guarantor replaces student affordability",
                +10,
                f"{_format_currency(guarantor_monthly_income)} guarantor income"
            )

            _add_reason(
                reasons,
                "Strong guarantor supports application."
            )

        else:

            score = _apply(
                score,
                breakdown,
                "Missing guarantor support",
                -45,
            )

            _add_reason(
                reasons,
                "Non-bursary students require guarantor income."
            )

            _add_action(
                actions,
                "Provide guarantor payslip and bank statements."
            )

    bands = suggested_budget_bands(effective_income)

    # ------------------------------------------------------------
    # Bursary logic
    # ------------------------------------------------------------

    affordability_skip = False

    if bursary_student:

        affordability_skip = True

        has_bursary = any(
            term in doc
            for doc in renter_docs_set
            for term in ["bursary", "nsfas", "award"]
        )

        if not has_bursary:

            score = _apply(
                score,
                breakdown,
                "Missing bursary proof",
                -35,
            )

            _add_reason(
                reasons,
                "Official bursary letter missing."
            )

            _add_action(
                actions,
                "Upload bursary award letter."
            )

        if monthly_income >= rent:

            buffer = monthly_income - rent

            if buffer >= 4000:
                score = _apply(score, breakdown, "Strong bursary coverage", +28)

            elif buffer >= 1500:
                score = _apply(score, breakdown, "Moderate bursary coverage", +12)

            else:
                score = _apply(score, breakdown, "Minimal bursary buffer", -8)

        else:

            shortfall = rent - monthly_income

            if shortfall <= 800:
                score = _apply(score, breakdown, "Small bursary shortfall", -18)

            elif shortfall <= 2000:
                score = _apply(score, breakdown, "Moderate bursary shortfall", -38)

            else:
                score = _apply(score, breakdown, "Large bursary shortfall", -65)

            _add_action(
                actions,
                "Add guarantor to offset bursary shortfall."
            )

    # ------------------------------------------------------------
    # Affordability logic
    # ------------------------------------------------------------

    if not affordability_skip:

        pct = _ratio_pct(rent, effective_income)

        if pct > 45:

            score = _apply(score, breakdown, "Extreme affordability risk", -70)

            _add_reason(
                reasons,
                "Rent far exceeds affordability."
            )

        elif pct > 38:

            score = _apply(score, breakdown, "High affordability risk", -50)

        elif pct > 33:

            score = _apply(score, breakdown, "Affordability warning", -25)

        else:

            _add_reason(
                reasons,
                "Rent within affordability range."
            )

    # ------------------------------------------------------------
    # Missing listing docs
    # ------------------------------------------------------------

    missing = required_docs_set - renter_docs_set

    if missing:

        score = _apply(
            score,
            breakdown,
            "Missing required listing documents",
            -20,
            ", ".join(missing),
        )

    # ------------------------------------------------------------
    # Demand adjustment
    # ------------------------------------------------------------

    if area_demand == "HIGH":

        score = _apply(score, breakdown, "High demand", -10)

    elif area_demand == "LOW":

        score = _apply(score, breakdown, "Low demand bonus", +5)

    # ------------------------------------------------------------
    # Upfront warning
    # ------------------------------------------------------------

    upfront = rent + deposit + application_fee

    if effective_income > 0 and upfront > effective_income:

        _add_reason(
            reasons,
            "Upfront costs high relative to income."
        )

    # ------------------------------------------------------------
    # Verdict
    # ------------------------------------------------------------

    score = max(0, min(100, score))

    if score >= 75:
        verdict = "WORTH_APPLYING"
        confidence = "HIGH"

    elif score >= 55:
        verdict = "BORDERLINE"
        confidence = "MEDIUM"

    else:
        verdict = "NOT_WORTH_IT"
        confidence = "LOW"

    _push_breakdown(
        breakdown,
        "Final verdict",
        0,
        score,
        score,
        verdict,
    )

    reasons, actions = _trim_output(reasons, actions)

    return (
        EvaluationResult(
            score=score,
            verdict=verdict,
            confidence=confidence,
            reasons=reasons,
            actions=actions,
            breakdown=breakdown,
        ),
        bands,
    )
