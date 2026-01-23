# -------------------------
# Document clusters
# -------------------------

DOC_CLUSTERS = {
    # Workers: strong evidence
    "worker": {"bank_statement", "payslip"},

    # New professional/recent grad: can apply with contract + guarantor
    "recent_grad": {"employment_contract", "guarantor_letter"},

    # Student
    "student": {"proof_of_registration", "proof_of_bursary", "guarantor_letter"},
}


def suggested_budget(monthly_income: int):
    return {
        "conservative": int(monthly_income * 0.25),
        "recommended": int(monthly_income * 0.30),
        "upper_limit": int(monthly_income * 0.35)
    }


def has_any_cluster_proof(docs: set[str]) -> bool:
    """
    Do they have any acceptable proof from any cluster?
    (doesn't replace bank statement, just reduces doc mismatch penalty)
    """
    for cluster_docs in DOC_CLUSTERS.values():
        if not docs.isdisjoint(cluster_docs):
            return True
    return False


def evaluate(renter, listing):
    score = 100
    reasons = []

    # --- Suggested rent budget info ---
    budget = suggested_budget(renter.monthly_income)

    # --- Rent vs income ---
    rent_ratio = listing.rent / renter.monthly_income
    if rent_ratio > 0.35:
        score -= 30
        reasons.append("Rent exceeds recommended affordability threshold")

    # --- Budget check ---
    if listing.rent > renter.budget:
        score -= 20
        reasons.append("Rent exceeds stated budget")

    # --- Deposit check ---
    if listing.deposit > renter.budget:
        score -= 10
        reasons.append("Deposit may be difficult to afford")

    # -------------------------
    # Document logic (clusters + universal bank statement penalty)
    # -------------------------
    renter_docs = set(renter.documents)
    required_docs = set(listing.required_documents)

    missing_required = required_docs - renter_docs
    has_proof = has_any_cluster_proof(renter_docs)
    has_bank_statement = "bank_statement" in renter_docs

    # 1) Required documents match / mismatch
    if not missing_required:
        score += 10
        reasons.append("All required documents are available")
    else:
        # Missing some required docs, but still has alternative proof
        if has_proof:
            score -= 10
            reasons.append("Some required documents are missing, but alternative proof is available")
        else:
            score -= 30
            reasons.append("Multiple required documents are missing")

    # 2) Universal penalty if no bank statement (applies to everyone)
    if not has_bank_statement:
        if has_proof:
            score -= 10
            reasons.append("No bank statement provided (may reduce application strength)")
        else:
            score -= 20
            reasons.append("No bank statement provided and limited alternative proof available")

    # --- Area demand ---
    if listing.area_demand == "HIGH":
        score -= 10
        reasons.append("High demand area increases competition")

    # --- Application fee (risk factor) ---
    if listing.application_fee > 0:
        fee_ratio = listing.application_fee / max(renter.budget, 1)

        if fee_ratio > 0.05:
            score -= 15
            reasons.append("High application fee relative to budget")

        if score < 60:
            score -= 10
            reasons.append("Application fee increases cost of a low-confidence application")

    # --- Clamp score ---
    score = max(0, min(score, 100))

    # --- Verdict ---
    if score >= 70:
        verdict = "WORTH_APPLYING"
    elif score >= 40:
        verdict = "BORDERLINE"
    else:
        verdict = "NOT_WORTH_IT"

    return score, verdict, reasons, budget
