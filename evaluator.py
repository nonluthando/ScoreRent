import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any


@dataclass
class EvaluationResult:
    score: int
    verdict: str
    confidence: str
    reasons: List[str]
    actions: List[str]
    breakdown: List[Dict[str, Any]]  # ✅ NEW


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


def _add_breakdown(breakdown: List[dict], title: str, delta: int, before: int, after: int, details: str = ""):
    breakdown.append(
        {
            "title": title,
            "delta": delta,
            "before": before,
            "after": after,
            "details": details,
        }
    )


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
    is_bursary_student: bool = False,   # ✅ NEW
) -> Tuple[EvaluationResult, Dict[str, int]]:
    reasons: List[str] = []
    actions: List[str] = []
    breakdown: List[dict] = []

    score = 70
    _add_breakdown(breakdown, "Base score", 0, 0, score, "All evaluations start at 70 and adjust per rules.")

    # ----------------------------
    # Normalise input
    # ----------------------------
    renter_type = (renter_type or "").strip().lower()
    renter_docs = set([d.strip().lower() for d in (renter_docs or []) if d.strip()])
    required_documents = set([d.strip().lower() for d in (required_documents or []) if d.strip()])
    area_demand = area_demand.upper().strip() if area_demand else "MEDIUM"

    if renter_type not in RENTER_TYPES:
        renter_type = "worker"

    if area_demand not in DEMAND_LEVELS:
        area_demand = "MEDIUM"

    is_student = renter_type == "student"
    has_bursary = is_student and bool(is_bursary_student)  # ✅ explicit question controls bursary rules
    non_bursary_student = is_student and not has_bursary

    # ----------------------------
    # Suggested budgets
    # For non-bursary students, affordability uses guarantor income
    # ----------------------------
    effective_income_for_affordability = monthly_income
    if non_bursary_student and guarantor_monthly_income > 0:
        effective_income_for_affordability = guarantor_monthly_income

    bands = suggested_budget_bands(effective_income_for_affordability)
    upper_limit = bands["upper_limit"]
    recommended = bands["recommended"]

    # ==========================================================
    # Student-specific rules
    # ==========================================================
    if is_student:
        if "proof_of_registration" not in renter_docs:
            before = score
            score -= 25
            _add_breakdown(breakdown, "Missing proof of registration", -25, before, score)
            reasons.append("Student applicants must provide proof of registration.")
            actions.append("Upload proof of registration.")

        if has_bursary:
            reasons.append("Bursary student selected (financial support assumed).")
        else:
            required_guarantor_docs = {"guarantor_letter", "guarantor_payslip", "guarantor_bank_statement"}
            missing = required_guarantor_docs - renter_docs
            if missing:
                before = score
                score -= 25
                _add_breakdown(
                    breakdown,
                    "Missing guarantor documentation (non-bursary student)",
                    -25,
                    before,
                    score,
                    details=", ".join(sorted(missing)),
                )
                reasons.append("Non-bursary student applications rely on guarantor documentation.")
                actions.append("Provide guarantor letter, guarantor payslip, and guarantor bank statement.")

            if guarantor_monthly_income <= 0:
                before = score
                score -= 15
                _add_breakdown(breakdown, "Guarantor income missing", -15, before, score)
                reasons.append("Guarantor income not provided.")
                actions.append("Insert guarantor monthly income to assess affordability.")

    # ==========================================================
    # Affordability rules
    # ==========================================================
    if non_bursary_student and guarantor_monthly_income <= 0:
        before = score
        score -= 10
        _add_breakdown(breakdown, "Affordability cannot be verified (no guarantor income)", -10, before, score)
        reasons.append("Affordability cannot be verified without guarantor income for a non-bursary student.")
        actions.append("Add guarantor income and re-evaluate affordability.")

    if rent > upper_limit:
        before = score
        score -= 30
        _add_breakdown(
            breakdown,
            "Affordability: rent exceeds 35% upper limit",
            -30,
            before,
            score,
            details=f"Upper limit: R{upper_limit}",
        )
        reasons.append("Rent exceeds the recommended affordability limit (35% of income).")
        actions.append("Target listings with rent <= 35% of monthly income.")
    elif rent > recommended:
        before = score
        score -= 12
        _add_breakdown(
            breakdown,
            "Affordability: rent above recommended 30%",
            -12,
            before,
            score,
            details=f"Recommended: R{recommended}",
        )
        reasons.append("Rent is above the recommended band (30% of income).")
        actions.append("If possible, reduce rent target closer to 30% of income.")
    else:
        before = score
        score += 5
        _add_breakdown(breakdown, "Affordability: within recommended range", +5, before, score)
        reasons.append("Rent falls within recommended affordability range.")

    # bursary: strong positive if covered
    if is_student and has_bursary and monthly_income >= rent:
        before = score
        score += 12
        _add_breakdown(breakdown, "Bursary covers rent", +12, before, score)
        reasons.append("Bursary/financial support covers rent (strong affordability signal).")
        actions.append("Apply — affordability looks strong for your situation.")

    # bursary shortfall
    if is_student and has_bursary and monthly_income < rent:
        shortfall = rent - monthly_income
        required_guarantor_income = math.ceil(shortfall / 0.30)

        reasons.append(f"Bursary does not fully cover rent (shortfall: R{shortfall}).")
        actions.append(
            f"Consider adding a guarantor: target guarantor income >= R{required_guarantor_income}/month "
            f"(so the shortfall stays within 30% affordability)."
        )

    # ==========================================================
    # Upfront cost risk (Informational only: no score penalty)
    # ==========================================================
    upfront = rent + deposit + application_fee
    if upfront > effective_income_for_affordability and effective_income_for_affordability > 0:
        reasons.append("Upfront cost (rent + deposit + application fee) is high relative to monthly income.")
        actions.append("Ensure deposit/fees are affordable before applying.")

    # ==========================================================
    # Required docs from listing
    # ==========================================================
    missing_required = required_documents - renter_docs
    if missing_required:
        before = score
        score -= 18
        _add_breakdown(
            breakdown,
            "Missing required listing documents",
            -18,
            before,
            score,
            details=", ".join(sorted(missing_required)),
        )
        reasons.append("Some required documents are missing.")
        actions.append("Gather the missing required documents before applying.")

    # ==========================================================
    # Cluster docs (recommended docs)
    # ONLY applies for new_professional + student
    # ==========================================================
    cluster_docs = DOC_CLUSTERS.get(renter_type, set())
    missing_cluster = cluster_docs - renter_docs

    if renter_type in {"new_professional", "student"}:
        if missing_cluster and len(missing_cluster) < len(cluster_docs):
            before = score
            score -= 6
            _add_breakdown(
                breakdown,
                "Missing recommended docs",
                -6,
                before,
                score,
                details=", ".join(sorted(missing_cluster)),
            )
            reasons.append("Some recommended documents for your renter category are missing.")
            actions.append("Add the recommended documents to strengthen your application.")

    # ==========================================================
    # Bank statement + payslip logic
    # ✅ FIX: no double penalty
    #   If listing already requires payslip and they’re missing it,
    #   don't also penalize again in worker rule.
    # ==========================================================
    if renter_type == "worker":
        payslip_missing = "payslip" not in renter_docs
        payslip_required_by_listing = "payslip" in required_documents

        if payslip_missing and not payslip_required_by_listing:
            before = score
            score -= 10
            _add_breakdown(breakdown, "Worker missing payslip", -10, before, score)
            reasons.append("No payslip provided (income verification is weak).")
            actions.append("Upload your latest payslip(s) to strengthen your application.")

        if "bank_statement" not in renter_docs:
            if "payslip" in renter_docs:
                before = score
                score -= 12
                _add_breakdown(breakdown, "Worker missing bank statement", -12, before, score)
                reasons.append("No bank statement provided (worker applications usually require it).")
                actions.append("Prepare 3 months bank statements before applying.")
            else:
                before = score
                score -= 18
                _add_breakdown(breakdown, "Worker missing bank statement + payslip", -18, before, score)
                reasons.append("No bank statement provided and payslip missing (very weak worker documentation).")
                actions.append("Prepare bank statements and payslips before applying.")

    elif renter_type == "new_professional":
        if "bank_statement" not in renter_docs:
            has_strong_np_docs = ("employment_contract" in renter_docs) and ("guarantor_letter" in renter_docs)
            if has_strong_np_docs:
                before = score
                score -= 6
                _add_breakdown(breakdown, "New professional missing bank statement (strong docs)", -6, before, score)
                reasons.append("No bank statement provided (supporting documents are strong).")
                actions.append("If possible, provide bank statements or alternative proof of income.")
            else:
                before = score
                score -= 10
                _add_breakdown(breakdown, "New professional missing bank statement", -10, before, score)
                reasons.append("No bank statement provided (may reduce application strength).")
                actions.append("Provide bank statements or supporting proof of income if possible.")

    elif renter_type == "student":
        if non_bursary_student and ("guarantor_bank_statement" not in renter_docs):
            before = score
            score -= 8
            _add_breakdown(breakdown, "Missing guarantor bank statement", -8, before, score)
            reasons.append("No guarantor bank statement provided (may weaken application).")
            actions.append("Ask guarantor for 3 months bank statements.")

    # ==========================================================
    # Demand weighting
    # ==========================================================
    if area_demand == "HIGH":
        before = score
        score -= 10
        _add_breakdown(breakdown, "High demand area", -10, before, score)
        reasons.append("High demand area increases competition.")
        actions.append("Apply only if documents and affordability are strong.")
    elif area_demand == "LOW":
        before = score
        score += 4
        _add_breakdown(breakdown, "Low demand area", +4, before, score)
        reasons.append("Lower demand area may reduce competition.")

    # Clamp score
    before = score
    score = max(0, min(100, score))
    if score != before:
        _add_breakdown(breakdown, "Final score clamp", 0, before, score)

    # ==========================================================
    # Verdict & Confidence
    # ==========================================================
    if score >= 75:
        verdict = "WORTH_APPLYING"
        confidence = "HIGH"
    elif score >= 55:
        verdict = "BORDERLINE"
        confidence = "MEDIUM"
    else:
        verdict = "NOT_WORTH_IT"
        confidence = "LOW"

    _add_breakdown(breakdown, "Verdict assigned", 0, score, score, details=f"{verdict} ({confidence})")

    # ==========================================================
    # Application fee logic (Informational only)
    # ==========================================================
    if application_fee >= 800:
        reasons.append("Application fee is high — consider the risk before applying.")
    elif application_fee >= 500:
        reasons.append("Application fee is moderate — consider the risk if unsure.")

    # ==========================================================
    # Suggested actions polish
    # ==========================================================
    if confidence == "HIGH":
        actions.insert(0, "Apply — this looks like a strong match.")
    elif confidence == "MEDIUM":
        actions.append("If possible, add a guarantor to strengthen your application.")
        if rent > recommended:
            actions.append("Consider roommates/house-sharing to reduce rent burden.")

    actions = _dedupe_keep_order(actions)[:5]
    reasons = _dedupe_keep_order(reasons)[:8]

    result = EvaluationResult(
        score=score,
        verdict=verdict,
        confidence=confidence,
        reasons=reasons,
        actions=actions,
        breakdown=breakdown,
    )

    return result, bands
