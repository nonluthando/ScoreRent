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


def _format_currency(value: int) -> str:
    return f"R{int(value):,}".replace(",", " ")


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
            "details": details or "",
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
    _push_breakdown(breakdown, title, int(delta), before, after, details=details)
    return after


def _ratio_pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 999.0
    return (numerator / denominator) * 100.0


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

    renter_type = (renter_type or "").strip().lower()
    if renter_type not in RENTER_TYPES:
        renter_type = "worker"

    renter_docs_set = set(d.strip().lower() for d in (renter_docs or []) if d and d.strip())
    required_docs_set = set(d.strip().lower() for d in (required_documents or []) if d and d.strip())

    area_demand = (area_demand or "MEDIUM").upper().strip()
    if area_demand not in DEMAND_LEVELS:
        area_demand = "MEDIUM"

    is_student = renter_type == "student"
    bursary_student = is_student and bool(is_bursary_student)
    non_bursary_student = is_student and not bursary_student

    has_employment_contract = "employment_contract" in renter_docs_set
    has_guarantor_letter = "guarantor_letter" in renter_docs_set

    score = 100
    _push_breakdown(
        breakdown,
        "Base confidence score",
        0,
        0,
        score,
        "Starts at 100 and is adjusted by affordability, document fit, and demand. "
        "This is NOT probability of acceptance.",
    )

    # ------------------------------------------------------------
    # Affordability (dominant signal)
    # ------------------------------------------------------------
    effective_income_for_affordability = int(monthly_income)

    # For non-bursary students, we can afford based on guarantor income
    if non_bursary_student and int(guarantor_monthly_income) > 0:
        effective_income_for_affordability = int(guarantor_monthly_income)

    bands = suggested_budget_bands(int(max(0, effective_income_for_affordability)))
    recommended = bands["recommended"]
    upper_limit = bands["upper_limit"]

    # Bursary: if bursary/support covers rent, skip affordability penalties entirely
    affordability_skip = bursary_student and int(monthly_income) >= int(rent)

    if bursary_student:
        reasons.append("Bursary student selected (financial support assumed).")

        if int(monthly_income) >= int(rent):
            score = _apply(score, breakdown, "Bursary/support covers rent", +10)
            reasons.append("Bursary/financial support covers rent.")
            actions.append("Apply — affordability looks strong for your situation.")
        else:
            shortfall = int(rent) - int(monthly_income)
            required_guarantor_income = math.ceil(shortfall / 0.30)
            reasons.append(f"Bursary does not fully cover rent (shortfall: {_format_currency(shortfall)}).")
            actions.append(
                f"Consider adding a guarantor: target guarantor income >= "
                f"{_format_currency(required_guarantor_income)}/month."
            )

    if not affordability_skip:
        pct = _ratio_pct(int(rent), int(effective_income_for_affordability))

        if pct > 40:
            score = _apply(
                score,
                breakdown,
                "Affordability: rent exceeds 40% of income",
                -70,
                details=f"Rent ratio: {pct:.0f}%",
            )
            reasons.append("Rent is extremely high relative to income (over 40%).")
            actions.append("Avoid — rent is too high for your income.")
        elif pct > 35:
            score = _apply(
                score,
                breakdown,
                "Affordability: rent exceeds 35% upper limit",
                -50,
                details=f"Upper limit: {_format_currency(upper_limit)}",
            )
            reasons.append("Rent exceeds affordability limit (over 35% of income).")
            actions.append("Avoid or look for cheaper listings.")
        elif pct > 30:
            score = _apply(
                score,
                breakdown,
                "Affordability: rent above recommended 30%",
                -30,
                details=f"Recommended: {_format_currency(recommended)}",
            )
            reasons.append("Rent is above recommended affordability (over 30% of income).")
            actions.append("If possible, reduce rent closer to 30% of income.")
        else:
            reasons.append("Rent is within recommended affordability range (≤ 30%).")

    # ------------------------------------------------------------
    # Student-specific doc logic
    # ------------------------------------------------------------
    if is_student:
        if "proof_of_registration" not in renter_docs_set:
            score = _apply(score, breakdown, "Missing proof of registration", -30)
            reasons.append("Student applicants must provide proof of registration.")
            actions.append("Upload proof of registration.")

        if non_bursary_student:
            required_guarantor_docs = {
                "guarantor_letter",
                "guarantor_payslip",
                "guarantor_bank_statement",
            }

            missing_guarantor_docs = required_guarantor_docs - renter_docs_set
            if missing_guarantor_docs:
                score = _apply(
                    score,
                    breakdown,
                    "Missing guarantor documentation",
                    -30,
                    details=", ".join(sorted(missing_guarantor_docs)),
                )
                reasons.append("Non-bursary student applications rely on guarantor documentation.")
                actions.append("Provide guarantor documentation (letter, payslip, bank statement).")

            if int(guarantor_monthly_income) <= 0:
                score = _apply(score, breakdown, "Guarantor income missing", -20)
                reasons.append("Guarantor income not provided.")
                actions.append("Insert guarantor monthly income to assess affordability.")

    # ------------------------------------------------------------
    # Required listing documents (cap penalty; no double punishment)
    # ------------------------------------------------------------
    missing_required = required_docs_set - renter_docs_set
    if missing_required:
        missing_count = len(missing_required)

        if missing_count == 1:
            delta = -15
        elif missing_count == 2:
            delta = -25
        else:
            delta = -30

        score = _apply(
            score,
            breakdown,
            "Missing required listing documents",
            delta,
            details=", ".join(sorted(missing_required)),
        )
        reasons.append("Some required listing documents are missing.")
        actions.append("Gather the missing documents required by the listing.")

    already_penalised_docs = set(missing_required)

    # ------------------------------------------------------------
    # Worker document rules
    # ------------------------------------------------------------
    if renter_type == "worker":
        if "payslip" not in renter_docs_set and "payslip" not in already_penalised_docs:
            score = _apply(score, breakdown, "Worker: missing payslip", -20)
            reasons.append("No payslip provided (income verification is weak).")
            actions.append("Upload your latest payslip(s).")

        if "bank_statement" not in renter_docs_set and "bank_statement" not in already_penalised_docs:
            if "payslip" in renter_docs_set:
                score = _apply(score, breakdown, "Worker: missing bank statement", -25)
                reasons.append("No bank statement provided (worker applications usually require it).")
                actions.append("Prepare 3 months bank statements.")
            else:
                score = _apply(score, breakdown, "Worker: missing bank statement + payslip", -35)
                reasons.append("Missing bank statement and payslip (very weak documentation).")
                actions.append("Prepare bank statements and payslips.")

    # ------------------------------------------------------------
    # New professional document rules (lighter penalties + boosts)
    # ------------------------------------------------------------
    if renter_type == "new_professional":
        if has_employment_contract:
            score = _apply(score, breakdown, "Employment contract provided", +8)
            reasons.append("Employment contract provided (strong proof of income).")

        if has_guarantor_letter:
            score = _apply(score, breakdown, "Guarantor letter provided", +5)
            reasons.append("Guarantor letter provided (supporting strength signal).")

        if "bank_statement" not in renter_docs_set and "bank_statement" not in already_penalised_docs:
            if not has_employment_contract:
                score = _apply(score, breakdown, "New professional: missing bank statement", -10)
                reasons.append("No bank statement provided (may weaken application).")
                actions.append("If possible, provide a bank statement or proof of income.")
            else:
                score = _apply(score, breakdown, "New professional: missing bank statement (contract present)", -4)

        if "payslip" not in renter_docs_set and "payslip" not in already_penalised_docs:
            if not has_employment_contract:
                score = _apply(score, breakdown, "New professional: missing payslip", -8)
                reasons.append("No payslip provided (may weaken application).")
                actions.append("Provide payslip or employment contract if available.")
            else:
                score = _apply(score, breakdown, "New professional: missing payslip (contract present)", -3)

    # ------------------------------------------------------------
    # Demand weighting (small factor)
    # ------------------------------------------------------------
    if area_demand == "HIGH":
        score = _apply(score, breakdown, "High demand area", -10)
        reasons.append("High demand area increases competition.")
        actions.append("Apply only if your documents and affordability are strong.")
    elif area_demand == "LOW":
        score = _apply(score, breakdown, "Low demand area", +5)
        reasons.append("Lower demand area may reduce competition.")

    # ------------------------------------------------------------
    # Application fee (informational only)
    # ------------------------------------------------------------
    if int(application_fee) >= 800:
        reasons.append("Application fee is high — consider the risk before applying.")
    elif int(application_fee) >= 500:
        reasons.append("Application fee is moderate — consider the risk if unsure.")

    # Upfront cost informational only
    upfront = int(rent) + int(deposit) + int(application_fee)
    if effective_income_for_affordability > 0 and upfront > effective_income_for_affordability:
        reasons.append("Upfront cost (rent + deposit + fee) is high relative to monthly income.")
        actions.append("Ensure deposit and fees are affordable before applying.")

    # ------------------------------------------------------------
    # Clamp and verdict
    # ------------------------------------------------------------
    before = score
    score = max(0, min(100, int(score)))
    if score != before:
        _push_breakdown(breakdown, "Final score clamp", 0, before, score)

    if score >= 75:
        verdict = "WORTH APPLYING"
        confidence = "HIGH"
    elif score >= 55:
        verdict = "BORDERLINE"
        confidence = "MEDIUM"
    else:
        verdict = "NOT WORTH IT"
        confidence = "LOW"

    _push_breakdown(breakdown, "Verdict assigned", 0, score, score, f"{verdict} ({confidence})")

    if confidence == "HIGH":
        actions.insert(0, "Apply — this looks like a strong match.")
    elif confidence == "MEDIUM":
        if any("rent above recommended" in b["title"].lower() for b in breakdown):
            actions.append("Consider roommates/house-sharing to reduce rent burden.")
        actions.append("Improve docs or affordability before applying.")

    actions = _dedupe_keep_order(actions)[:6]
    reasons = _dedupe_keep_order(reasons)[:10]

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
