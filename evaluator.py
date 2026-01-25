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
    breakdown: List[Dict[str, Any]]  # ✅ new


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
) -> Tuple[EvaluationResult, Dict[str, int]]:
    reasons: List[str] = []
    actions: List[str] = []

    breakdown: List[Dict[str, Any]] = []
    score = 70
    breakdown.append({"label": "Base score", "delta": 70, "kind": "base"})

    def add_breakdown(label: str, delta: int, kind: str):
        nonlocal score
        score += delta
        breakdown.append({"label": label, "delta": delta, "kind": kind})

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
    has_bursary = is_student and ("bursary_letter" in renter_docs)
    non_bursary_student = is_student and not has_bursary

    # ----------------------------
    # Suggested budgets
    # ----------------------------
    effective_income_for_affordability = monthly_income
    if non_bursary_student and guarantor_monthly_income > 0:
        effective_income_for_affordability = guarantor_monthly_income

    bands = suggested_budget_bands(effective_income_for_affordability)
    upper_limit = bands["upper_limit"]
    recommended = bands["recommended"]

    # ==========================================================
    # Student-specific document requirements
    # ==========================================================
    if is_student:
        if "proof_of_registration" not in renter_docs:
            add_breakdown("Missing proof of registration (student)", -25, "student_docs")
            reasons.append("Student applicants must provide proof of registration.")
            actions.append("Upload proof of registration.")

        if has_bursary:
            reasons.append("Bursary confirmation provided (strong financial support).")
        else:
            required_guarantor_docs = {
                "guarantor_letter",
                "guarantor_payslip",
                "guarantor_bank_statement",
            }
            missing = required_guarantor_docs - renter_docs
            if missing:
                add_breakdown("Missing guarantor documentation (non-bursary student)", -25, "student_docs")
                reasons.append("Non-bursary student applications rely on guarantor documentation.")
                actions.append("Provide guarantor letter, guarantor payslip, and guarantor bank statement.")

            if guarantor_monthly_income <= 0:
                add_breakdown("Guarantor income not provided", -15, "student_affordability")
                reasons.append("Guarantor income not provided.")
                actions.append("Insert guarantor monthly income to assess affordability.")

    # ==========================================================
    # Affordability rules
    # ==========================================================
    if non_bursary_student and guarantor_monthly_income <= 0:
        add_breakdown("Affordability cannot be verified without guarantor income", -10, "affordability")
        reasons.append("Affordability cannot be verified without guarantor income for a non-bursary student.")
        actions.append("Add guarantor income and re-evaluate affordability.")

    if rent > upper_limit:
        add_breakdown("Rent exceeds upper affordability limit (35%)", -30, "affordability")
        reasons.append("Rent exceeds the recommended affordability limit (35% of income).")
        actions.append("Target listings with rent <= 35% of monthly income.")
    elif rent > recommended:
        add_breakdown("Rent above recommended band (30%)", -12, "affordability")
        reasons.append("Rent is above the recommended band (30% of income).")
        actions.append("If possible, reduce rent target closer to 30% of income.")
    else:
        add_breakdown("Rent within affordability band", +5, "affordability")
        reasons.append("Rent falls within recommended affordability range.")

    if is_student and has_bursary and monthly_income >= rent:
        add_breakdown("Bursary support covers rent", +12, "student_affordability")
        reasons.append("Bursary/financial support covers rent (strong affordability signal).")
        actions.append("Apply — affordability looks strong for your situation.")

    if is_student and has_bursary and monthly_income < rent:
        shortfall = rent - monthly_income
        required_guarantor_income = math.ceil(shortfall / 0.30)

        reasons.append(f"Bursary does not fully cover rent (shortfall: R{shortfall}).")
        actions.append(
            f"Consider adding a guarantor: target guarantor income >= R{required_guarantor_income}/month "
            f"(so the shortfall stays within 30% affordability)."
        )

    # ==========================================================
    # Upfront cost risk (informational only)
    # ==========================================================
    upfront = rent + deposit + application_fee
    if upfront > effective_income_for_affordability and effective_income_for_affordability > 0:
        # informational only: breakdown item with delta 0
        breakdown.append({"label": "Upfront cost high (informational)", "delta": 0, "kind": "info"})
        reasons.append("Upfront cost (rent + deposit + application fee) is high relative to monthly income.")
        actions.append("Ensure deposit/fees are affordable before applying.")

    # ==========================================================
    # Required documents from listing
    # ==========================================================
    missing_required = required_documents - renter_docs
    if missing_required:
        add_breakdown("Missing listing required documents", -18, "listing_docs")
        reasons.append("Some required documents are missing.")
        actions.append("Gather the missing required documents before applying.")

    # ==========================================================
    # Cluster docs (recommended docs)
    # only student + new_professional
    # ==========================================================
    cluster_docs = DOC_CLUSTERS.get(renter_type, set())
    missing_cluster = cluster_docs - renter_docs

    if renter_type in {"new_professional", "student"}:
        if missing_cluster and len(missing_cluster) < len(cluster_docs):
            add_breakdown("Missing recommended documents (renter category)", -6, "recommended_docs")
            reasons.append("Some recommended documents for your renter category are missing.")
            actions.append("Add the recommended documents to strengthen your application.")

    # ==========================================================
    # Bank statement + payslip logic
    # ==========================================================
    if renter_type == "worker":
        if "payslip" not in renter_docs:
            add_breakdown("Missing payslip (worker)", -10, "worker_docs")
            reasons.append("No payslip provided (income verification is weak).")
            actions.append("Upload your latest payslip(s) to strengthen your application.")

        if "bank_statement" not in renter_docs:
            if "payslip" in renter_docs:
                add_breakdown("Missing bank statement (worker)", -12, "worker_docs")
                reasons.append("No bank statement provided (worker applications usually require it).")
                actions.append("Prepare 3 months bank statements before applying.")
            else:
                add_breakdown("Missing bank statement + payslip (worker)", -18, "worker_docs")
                reasons.append("No bank statement provided and payslip missing (very weak worker documentation).")
                actions.append("Prepare bank statements and payslips before applying.")

    elif renter_type == "new_professional":
        if "bank_statement" not in renter_docs:
            has_strong_np_docs = ("employment_contract" in renter_docs) and ("guarantor_letter" in renter_docs)
            if has_strong_np_docs:
                add_breakdown("Missing bank statement (new professional, strong docs)", -6, "np_docs")
                reasons.append("No bank statement provided (supporting documents are strong).")
                actions.append("If possible, provide bank statements or alternative proof of income.")
            else:
                add_breakdown("Missing bank statement (new professional)", -10, "np_docs")
                reasons.append("No bank statement provided (may reduce application strength).")
                actions.append("Provide bank statements or supporting proof of income if possible.")

    elif renter_type == "student":
        if non_bursary_student and ("guarantor_bank_statement" not in renter_docs):
            add_breakdown("Missing guarantor bank statement (student)", -8, "student_docs")
            reasons.append("No guarantor bank statement provided (may weaken application).")
            actions.append("Ask guarantor for 3 months bank statements.")

    # ==========================================================
    # Demand weighting
    # ==========================================================
    if area_demand == "HIGH":
        add_breakdown("High demand area (more competition)", -10, "demand")
        reasons.append("High demand area increases competition.")
        actions.append("Apply only if documents and affordability are strong.")
    elif area_demand == "LOW":
        add_breakdown("Low demand area (less competition)", +4, "demand")
        reasons.append("Lower demand area may reduce competition.")

    # Clamp score
    score = max(0, min(100, score))

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

    # ==========================================================
    # Application fee logic (informational only)
    # ==========================================================
    if application_fee >= 800:
        breakdown.append({"label": "High application fee (informational)", "delta": 0, "kind": "info"})
        reasons.append("Application fee is high — consider the risk before applying.")
    elif application_fee >= 500:
        breakdown.append({"label": "Moderate application fee (informational)", "delta": 0, "kind": "info"})
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
