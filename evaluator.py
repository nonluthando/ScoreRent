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


def _verdict(score: int) -> Tuple[str, str]:
    if score >= 75:
        return "WORTH_APPLYING", "HIGH"
    if score >= 55:
        return "BORDERLINE", "MEDIUM"
    return "NOT_WORTH_IT", "LOW"


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

    renter_type = (renter_type or "").strip().lower()
    renter_docs_set = set(d.strip().lower() for d in (renter_docs or []) if d and d.strip())
    required_docs_set = set(d.strip().lower() for d in (required_documents or []) if d and d.strip())
    area_demand = (area_demand or "MEDIUM").upper().strip()

    if renter_type not in RENTER_TYPES:
        renter_type = "worker"

    if area_demand not in DEMAND_LEVELS:
        area_demand = "MEDIUM"

    is_student = renter_type == "student"
    bursary_student = is_student and bool(is_bursary_student)  # checkbox-first
    non_bursary_student = is_student and not bursary_student

    if non_bursary_student and "bursary_letter" in renter_docs_set:
        reasons.append("Bursary letter uploaded, but bursary status not selected (treating as non-bursary).")

    effective_income_for_affordability = int(monthly_income or 0)
    if non_bursary_student and int(guarantor_monthly_income or 0) > 0:
        effective_income_for_affordability = int(guarantor_monthly_income or 0)

    bands = suggested_budget_bands(int(effective_income_for_affordability))
    recommended = bands["recommended"]
    upper_limit = bands["upper_limit"]

    # Student rules
    if is_student:
        if "proof_of_registration" not in renter_docs_set:
            score = _apply(score, breakdown, "Missing proof of registration", -25)
            reasons.append("Student applicants must provide proof of registration.")
            actions.append("Upload proof of registration.")

        if bursary_student:
            reasons.append("Bursary student selected (financial support assumed).")

            if monthly_income >= rent:
                score = _apply(score, breakdown, "Bursary/support covers rent", +10)
                reasons.append("Bursary/financial support covers the rent.")
                actions.append("Apply — affordability looks strong for your situation.")
            else:
                shortfall = rent - monthly_income
                required_guarantor_income = math.ceil(shortfall / 0.30)

                score = _apply(score, breakdown, "Bursary shortfall", -8, details=f"Shortfall: {_format_currency(shortfall)}")
                reasons.append(f"Bursary does not fully cover rent (shortfall: {_format_currency(shortfall)}).")
                actions.append(
                    "Consider adding a guarantor to cover the shortfall "
                    f"(target guarantor income >= {_format_currency(required_guarantor_income)}/month)."
                )

        else:
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
                    -20,
                    details=", ".join(sorted(missing_guarantor_docs)),
                )
                reasons.append("Non-bursary student applications rely on guarantor documentation.")
                actions.append("Provide guarantor documentation (letter, payslip, bank statement).")

            if guarantor_monthly_income <= 0:
                score = _apply(score, breakdown, "Guarantor income missing", -15)
                reasons.append("Guarantor income not provided.")
                actions.append("Insert guarantor monthly income to assess affordability.")

    # Affordability
    affordability_skipped = bursary_student and monthly_income >= rent
    if affordability_skipped:
        reasons.append("Affordability penalty skipped because bursary/support covers rent.")
    else:
        if effective_income_for_affordability <= 0:
            score = _apply(score, breakdown, "Affordability cannot be verified", -12)
            reasons.append("Affordability cannot be verified (income missing/zero).")
            actions.append("Add income (or guarantor income for non-bursary students) and re-evaluate.")
        else:
            if rent > upper_limit:
                score = _apply(
                    score,
                    breakdown,
                    "Affordability: rent exceeds 35% upper limit",
                    -30,
                    details=f"Upper limit: {_format_currency(upper_limit)}",
                )
                reasons.append("Rent exceeds the recommended affordability limit (35% of income).")
                actions.append("Target listings with rent <= 35% of monthly income.")
            elif rent > recommended:
                score = _apply(
                    score,
                    breakdown,
                    "Affordability: rent above recommended 30%",
                    -12,
                    details=f"Recommended: {_format_currency(recommended)}",
                )
                reasons.append("Rent is above the recommended band (30% of income).")
                actions.append("If possible, reduce rent target closer to 30% of income.")
            else:
                score = _apply(score, breakdown, "Affordability: within recommended range", +5)
                reasons.append("Rent falls within recommended affordability range.")

    # Upfront costs informational only
    upfront = rent + deposit + application_fee
    if effective_income_for_affordability > 0 and upfront > effective_income_for_affordability:
        reasons.append("Upfront cost (rent + deposit + application fee) is high relative to monthly income.")
        actions.append("Ensure deposit and fees are affordable before applying.")

    # Listing required documents
    missing_required = required_docs_set - renter_docs_set
    if missing_required:
        score = _apply(
            score,
            breakdown,
            "Missing required listing documents",
            -18,
            details=", ".join(sorted(missing_required)),
        )
        reasons.append("Some required documents are missing.")
        actions.append("Gather the missing documents required by the listing.")

    # Recommended docs clusters (soft signals only)
    if renter_type in {"student", "new_professional"}:
        cluster_docs = DOC_CLUSTERS.get(renter_type, set())
        missing_cluster = cluster_docs - renter_docs_set

        if missing_cluster and len(missing_cluster) < len(cluster_docs):
            score = _apply(
                score,
                breakdown,
                "Missing recommended documents",
                -6,
                details=", ".join(sorted(missing_cluster)),
            )
            reasons.append("Some recommended documents for your renter category are missing.")
            actions.append("Add recommended supporting documents to strengthen the application.")

    # Worker rules
    if renter_type == "worker":
        payslip_missing = "payslip" not in renter_docs_set
        payslip_required_by_listing = "payslip" in required_docs_set

        if payslip_missing and not payslip_required_by_listing:
            score = _apply(score, breakdown, "Worker: missing payslip", -15)
            reasons.append("No payslip provided (income verification is weak).")
            actions.append("Upload your latest payslip(s) to strengthen your application.")

        if "bank_statement" not in renter_docs_set:
            if "payslip" in renter_docs_set:
                score = _apply(score, breakdown, "Worker: missing bank statement", -15)
                reasons.append("No bank statement provided (worker applications usually require it).")
                actions.append("Prepare 3 months bank statements before applying.")
            else:
                score = _apply(score, breakdown, "Worker: missing bank statement + payslip", -25)
                reasons.append("Missing bank statement and payslip (very weak income documentation).")
                actions.append("Prepare bank statements and payslips before applying.")

    # New professional rules
    if renter_type == "new_professional":
        has_employment_contract = "employment_contract" in renter_docs_set
        has_guarantor_letter = "guarantor_letter" in renter_docs_set

        if has_employment_contract:
            score = _apply(score, breakdown, "New professional: employment contract provided", +12)
            reasons.append("Employment contract provided (strong proof of income).")

        if has_guarantor_letter:
            score = _apply(score, breakdown, "New professional: guarantor letter provided", +6)
            reasons.append("Guarantor letter provided (supporting strength signal).")

        if "bank_statement" not in renter_docs_set and not has_employment_contract:
            score = _apply(score, breakdown, "New professional: missing bank statement", -8)
            reasons.append("No bank statement provided (and no strong alternative proof).")
            actions.append("If possible, provide bank statements or an employment contract.")

        if "payslip" not in renter_docs_set and not has_employment_contract:
            score = _apply(score, breakdown, "New professional: missing payslip", -6)
            reasons.append("No payslip provided (and no strong alternative proof).")
            actions.append("Provide payslip or employment contract if available.")

    # Demand weighting
    if area_demand == "HIGH":
        score = _apply(score, breakdown, "High demand area", -10)
        reasons.append("High demand area increases competition.")
        actions.append("Apply only if documents and affordability are strong.")
    elif area_demand == "LOW":
        score = _apply(score, breakdown, "Low demand area", +4)
        reasons.append("Lower demand area may reduce competition.")

    # Clamp
    before = score
    score = max(0, min(100, score))
    if score != before:
        _push_breakdown(breakdown, "Final score clamp", 0, before, score)

    verdict, confidence = _verdict(score)
    _push_breakdown(breakdown, "Verdict assigned", 0, score, score, f"{verdict} ({confidence})")

    # Application fee informational only
    if application_fee >= 800:
        reasons.append("Application fee is high — consider the risk before applying.")
    elif application_fee >= 500:
        reasons.append("Application fee is moderate — consider the risk if unsure.")

    # Suggested actions
    if confidence == "HIGH":
        actions.insert(0, "Apply — this looks like a strong match.")
    elif confidence == "MEDIUM":
        actions.append("If possible, add a guarantor to strengthen your application.")
        if rent > recommended and not bursary_student:
            actions.append("Consider roommates/house-sharing to reduce rent burden.")

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
