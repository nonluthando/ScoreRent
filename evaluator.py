import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


# ------------------------------------------------------------
# Market configuration (Cape Town only)
# ------------------------------------------------------------

APP_MARKET = "Cape Town"

CURRENCY_CODE = "ZAR"
CURRENCY_SYMBOL = "R"

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
    except Exception:
        return 0


def _format_currency(value: int) -> str:
    value = _money(value)
    return f"{CURRENCY_SYMBOL}{value:,}".replace(",", " ")


# ------------------------------------------------------------
# Budget bands
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

    renter_docs_set = set(d.strip().lower() for d in renter_docs or [])
    required_docs_set = set(d.strip().lower() for d in required_documents or [])

    area_demand = (area_demand or "MEDIUM").upper()
    if area_demand not in DEMAND_LEVELS:
        area_demand = "MEDIUM"

    is_student = renter_type == "student"
    bursary_student = is_student and is_bursary_student
    non_bursary_student = is_student and not is_bursary_student

    score = 100

    _push_breakdown(
        breakdown,
        "Base match score",
        0,
        0,
        score,
        f"Evaluation calibrated for {APP_MARKET} rental market (2026).",
    )

    effective_income = monthly_income

    # ---------------- Non-bursary student guarantor logic ----------------

    if non_bursary_student:

        has_letter = any("letter" in d and "guarantor" in d for d in renter_docs_set)
        has_payslip = any("payslip" in d and "guarantor" in d for d in renter_docs_set)
        has_bank = any("bank" in d and "guarantor" in d for d in renter_docs_set)

        guarantor_docs_complete = has_letter and has_payslip and has_bank

        if guarantor_docs_complete and guarantor_monthly_income > 0:

            effective_income = guarantor_monthly_income

            score = _apply(
                score,
                breakdown,
                "Guarantor fully supports affordability",
                +18,
                f"Guarantor income {_format_currency(guarantor_monthly_income)}",
            )

            _add_reason(
                reasons,
                "Application supported by financially qualified guarantor.",
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
                "Non-bursary students typically require full guarantor support.",
            )

            _add_action(
                actions,
                "Provide guarantor letter, payslip, and bank statements.",
            )

    # ---------------- Bursary logic ----------------

    affordability_skip = False

    if bursary_student:

        affordability_skip = True

        has_bursary_proof = any(
            term in doc
            for doc in renter_docs_set
            for term in ["bursary", "nsfas", "award"]
        )

        if not has_bursary_proof:

            score = _apply(
                score,
                breakdown,
                "Missing official bursary confirmation letter",
                -35,
            )

            _add_reason(
                reasons,
                "Official bursary award letter is missing.",
            )

        shortfall = rent - monthly_income

        if shortfall > 0:

            score = _apply(
                score,
                breakdown,
                "Bursary shortfall",
                -38,
                f"Shortfall {_format_currency(shortfall)}",
            )

            _add_reason(
                reasons,
                "Bursary does not fully cover rent.",
            )

            _add_action(
                actions,
                "Add guarantor income to strengthen application.",
            )

        else:

            score = _apply(
                score,
                breakdown,
                "Bursary covers rent",
                +20,
            )

    # ---------------- Proportional affordability ----------------

    if not affordability_skip:

        pct = _ratio_pct(rent, effective_income) / 100.0

        recommended = CAPE_TOWN_RECOMMENDED_CAP
        extreme = CAPE_TOWN_EXTREME_CAP

        if pct <= recommended:

            _add_reason(
                reasons,
                "Rent is within safe approval range for Cape Town.",
            )

        else:

            max_penalty = 70
            risk_range = extreme - recommended
            over_ratio = min(pct, extreme) - recommended

            proportional_penalty = int((over_ratio / risk_range) * max_penalty)

            score = _apply(
                score,
                breakdown,
                "Affordability risk (proportional)",
                -proportional_penalty,
                f"{pct*100:.0f}% of income",
            )

            if pct >= extreme:

                _add_reason(
                    reasons,
                    "Rent is far above typical approval range for Cape Town.",
                )

    # ---------------- Required documents ----------------

    missing_required = required_docs_set - renter_docs_set

    if missing_required:

        score = _apply(
            score,
            breakdown,
            "Missing required documents",
            -20,
        )

    # ---------------- Demand ----------------

    if area_demand == "HIGH":
        score = _apply(score, breakdown, "High demand area", -10)
    elif area_demand == "LOW":
        score = _apply(score, breakdown, "Low demand area", +5)

    # ---------------- Upfront warning only ----------------

    if monthly_income > 0:

        upfront_cost = rent + deposit + application_fee
        upfront_ratio = upfront_cost / monthly_income

        if upfront_ratio > 3.0:
            _add_reason(
                reasons,
                "Upfront cost is very high relative to monthly income.",
            )
            _add_action(
                actions,
                "Ensure sufficient savings are available before applying.",
            )
        elif upfront_ratio > 2.0:
            _add_reason(
                reasons,
                "Upfront cost may be difficult to mobilize quickly.",
            )
        elif upfront_ratio > 1.2:
            _add_reason(
                reasons,
                "Upfront cost is moderately high compared to income.",
            )

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
        f"{verdict} ({confidence})",
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
        suggested_budget_bands(effective_income),
    )
