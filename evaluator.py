import math
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class EvaluationResult:
    score: int
    verdict: str
    confidence: str
    reasons: List[str]
    actions: List[str]


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
    score = 70

    # ---- Normalise input ----
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

    # ---- Suggested budgets ----
    # For non-bursary students, affordability should be evaluated using GUARANTOR income
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
        # proof of registration required for ALL students
        if "proof_of_registration" not in renter_docs:
            score -= 25
            reasons.append("Student applicants must provide proof of registration.")
            actions.append("Upload proof of registration.")

        if has_bursary:
            # bursary confirmation required
            reasons.append("Bursary confirmation provided (strong financial support).")
        else:
            # Non-bursary students require guarantor support
            required_guarantor_docs = {
                "guarantor_letter",
                "guarantor_payslip",
                "guarantor_bank_statement",
            }
            missing = required_guarantor_docs - renter_docs
            if missing:
                score -= 25
                reasons.append("Non-bursary student applications rely on guarantor documentation.")
                actions.append("Provide guarantor letter, guarantor payslip, and guarantor bank statement.")

            if guarantor_monthly_income <= 0:
                score -= 15
                reasons.append("Guarantor income not provided.")
                actions.append("Insert guarantor monthly income to assess affordability.")

    # ==========================================================
    # Affordability rules
    # ==========================================================
    # If non-bursary student and no guarantor income, treat as weak signal
    if non_bursary_student and guarantor_monthly_income <= 0:
        score -= 10
        reasons.append("Affordability cannot be verified without guarantor income for a non-bursary student.")
        actions.append("Add guarantor income and re-evaluate affordability.")

    # Standard affordability logic (but based on effective income for affordability)
    if rent > upper_limit:
        score -= 30
        reasons.append("Rent exceeds the recommended affordability limit (35% of income).")
        actions.append("Target listings with rent <= 35% of monthly income.")
    elif rent > recommended:
        score -= 12
        reasons.append("Rent is above the recommended band (30% of income).")
        actions.append("If possible, reduce rent target closer to 30% of income.")
    else:
        score += 5
        reasons.append("Rent falls within recommended affordability range.")

    # Bursary student: if bursary/monthly support covers rent, strong positive
    if is_student and has_bursary and monthly_income >= rent:
        score += 12
        reasons.append("Bursary/financial support covers rent (strong affordability signal).")
        actions.append("Apply — affordability looks strong for your situation.")

    # Bursary shortfall: recommend guarantor income that keeps deficit <= 30% of guarantor income
    if is_student and has_bursary and monthly_income < rent:
        shortfall = rent - monthly_income
        required_guarantor_income = math.ceil(shortfall / 0.30)

        reasons.append(f"Bursary does not fully cover rent (shortfall: R{shortfall}).")
        actions.append(
            f"Consider adding a guarantor: target guarantor income >= R{required_guarantor_income}/month "
            f"(so the shortfall stays within 30% affordability)."
        )

    # ==========================================================
    # Upfront cost risk (✅ informational only: no penalty)
    # ==========================================================
    upfront = rent + deposit + application_fee
    if upfront > effective_income_for_affordability and effective_income_for_affordability > 0:
        reasons.append("Upfront cost (rent + deposit + application fee) is high relative to monthly income.")
        actions.append("Ensure deposit/fees are affordable before applying.")

    # ==========================================================
    # Required documents from listing
    # ==========================================================
    missing_required = required_documents - renter_docs
    if missing_required:
        score -= 18
        reasons.append("Some required documents are missing.")
        actions.append("Gather the missing required documents before applying.")

 # Cluster docs (recommended docs for category)
cluster_docs = DOC_CLUSTERS.get(renter_type, set())
missing_cluster = cluster_docs - renter_docs

# Only apply cluster penalty for renter types where these docs are "soft signals"
# (for workers, docs are handled explicitly as hard requirements)
if renter_type in {"new_professional", "student"}:
    if missing_cluster and len(missing_cluster) < len(cluster_docs):
        score -= 6
        reasons.append("Some recommended documents for your renter category are missing.")
        actions.append("Add the recommended documents to strengthen your application.")

    # ==========================================================
    # Bank statement logic (UPDATED)
    # ==========================================================
    if not is_student:
        if renter_type == "worker":
           if "payslip" not in renter_docs:
        score -= 10
        reasons.append("No payslip provided (income verification is weak).")
        actions.append("Upload your latest payslip(s) to strengthen your application.")
            # Heavy penalty if worker missing bank statement
            if "bank_statement" not in renter_docs:
                # If they at least have payslip, reduce slightly
                if "payslip" in renter_docs:
                    score -= 12
                    reasons.append("No bank statement provided (worker applications usually require it).")
                    actions.append("Prepare 3 months bank statements before applying.")
                else:
                    score -= 18
                    reasons.append("No bank statement provided and payslip missing (very weak worker documentation).")
                    actions.append("Prepare bank statements and payslips before applying.")

        elif renter_type == "new_professional":
            #Lighter penalty if they have strong docs (employment contract + guarantor)
            if "bank_statement" not in renter_docs:
                has_strong_np_docs = ("employment_contract" in renter_docs) and ("guarantor_letter" in renter_docs)
                if has_strong_np_docs:
                    score -= 6
                    reasons.append("No bank statement provided (may reduce strength, but supporting documents are strong).")
                    actions.append("If possible, provide bank statements or alternative proof of income.")
                else:
                    score -= 10
                    reasons.append("No bank statement provided (may reduce application strength).")
                    actions.append("Provide bank statements or supporting proof of income if possible.")

        else:
            # fallback
            if "bank_statement" not in renter_docs:
                score -= 10
                reasons.append("No bank statement provided (may reduce application strength).")
                actions.append("Prepare 3 months bank statements if available.")

    else:
        # students:
        # bursary students do NOT need bank statement
        if non_bursary_student and ("guarantor_bank_statement" not in renter_docs):
            score -= 8
            reasons.append("No guarantor bank statement provided (may weaken application).")
            actions.append("Ask guarantor for 3 months bank statements.")

    # ==========================================================
    # Demand weighting
    # ==========================================================
    if area_demand == "HIGH":
        score -= 10
        reasons.append("High demand area increases competition.")
        actions.append("Apply only if documents and affordability are strong.")
    elif area_demand == "LOW":
        score += 4
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
    # Application fee logic
    # - If confidence MEDIUM: informational note, no penalty
    # ==========================================================
    if confidence == "MEDIUM":
        if application_fee >= 800:
            reasons.append("Application fee is high — consider the risk before applying.")
        elif application_fee >= 500:
            reasons.append("Application fee is moderate — consider the risk if unsure.")
    else:
        if application_fee >= 800:
            score -= 8
            reasons.append("High application fee increases cost of a low-confidence application.")
            actions.append("Avoid high-fee applications unless score is strong.")
        elif application_fee >= 500:
            score -= 4
            reasons.append("Moderate application fee increases risk if application is weak.")

        score = max(0, min(100, score))
        # re-evaluate confidence in case fee changed the score
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
    # Suggested actions polish
    # ==========================================================
    if confidence == "HIGH":
        actions.insert(0, "Apply — this looks like a strong match.")

    elif confidence == "MEDIUM":
        # suggest guarantor only if missing guarantor / borderline student gaps
        actions.append("If possible, add a guarantor to strengthen your application.")

        # ✅ roommate suggestion if affordability is tight (rent above recommended)
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
    )

    return result, bands
