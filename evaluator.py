import math
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class ScoreStep:
    label: str
    delta: int
    score_after: int
    note: str = ""


@dataclass
class EvaluationResult:
    score: int
    verdict: str
    confidence: str
    reasons: List[str]
    actions: List[str]
    breakdown: List[ScoreStep]  # ✅ NEW


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
    breakdown: List[ScoreStep] = []

    def add_step(label: str, delta: int, note: str = ""):
        nonlocal score
        score += delta
        breakdown.append(
            ScoreStep(label=label, delta=delta, score_after=score, note=note)
        )

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

    breakdown.append(
        ScoreStep(
            label="Base score",
            delta=0,
            score_after=score,
            note="All evaluations start at 70 and adjust per rules.",
        )
    )

    # ----------------------------
    # Suggested budgets
    # For non-bursary students, affordability uses guarantor income
    # ----------------------------
    effective_income_for_affordability = monthly_income
    if non_bursary_student and guarantor_monthly_income > 0:
        effective_income_for_affordability = guarantor_monthly_income
        breakdown.append(
            ScoreStep(
                label="Affordability income source",
                delta=0,
                score_after=score,
                note="Non-bursary student: using guarantor income for affordability.",
            )
        )

    bands = suggested_budget_bands(effective_income_for_affordability)
    upper_limit = bands["upper_limit"]
    recommended = bands["recommended"]

    # ==========================================================
    # Student-specific document requirements
    # ==========================================================
    if is_student:
        if "proof_of_registration" not in renter_docs:
            add_step("Missing proof of registration", -25)
            reasons.append("Student applicants must provide proof of registration.")
            actions.append("Upload proof of registration.")

        if has_bursary:
            breakdown.append(ScoreStep("Bursary confirmation", 0, score, "Bursary provided (strong signal)."))
            reasons.append("Bursary confirmation provided (strong financial support).")
        else:
            required_guarantor_docs = {
                "guarantor_letter",
                "guarantor_payslip",
                "guarantor_bank_statement",
            }
            missing = required_guarantor_docs - renter_docs
            if missing:
                add_step("Missing guarantor documents (non-bursary student)", -25)
                reasons.append("Non-bursary student applications rely on guarantor documentation.")
                actions.append("Provide guarantor letter, guarantor payslip, and guarantor bank statement.")

            if guarantor_monthly_income <= 0:
                add_step("Guarantor income not provided", -15)
                reasons.append("Guarantor income not provided.")
                actions.append("Insert guarantor monthly income to assess affordability.")

    # ==========================================================
    # Affordability rules
    # ==========================================================
    if non_bursary_student and guarantor_monthly_income <= 0:
        add_step("Non-bursary student affordability unverifiable", -10)
        reasons.append("Affordability cannot be verified without guarantor income for a non-bursary student.")
        actions.append("Add guarantor income and re-evaluate affordability.")

    if rent > upper_limit:
        add_step("Affordability: rent exceeds 35% upper limit", -30, note=f"Upper limit: R{upper_limit}")
        reasons.append("Rent exceeds the recommended affordability limit (35% of income).")
        actions.append("Target listings with rent <= 35% of monthly income.")
    elif rent > recommended:
        add_step("Affordability: rent above 30% recommended band", -12, note=f"Recommended: R{recommended}")
        reasons.append("Rent is above the recommended band (30% of income).")
        actions.append("If possible, reduce rent target closer to 30% of income.")
    else:
        add_step("Affordability: within recommended range", +5)
        reasons.append("Rent falls within recommended affordability range.")

    # bursary: strong positive if covered
    if is_student and has_bursary and monthly_income >= rent:
        add_step("Bursary covers rent (strong positive)", +12)
        reasons.append("Bursary/financial support covers rent (strong affordability signal).")
        actions.append("Apply — affordability looks strong for your situation.")

    # bursary shortfall
    if is_student and has_bursary and monthly_income < rent:
        shortfall = rent - monthly_income
        required_guarantor_income = math.ceil(shortfall / 0.30)

        breakdown.append(
            ScoreStep(
                label="Bursary shortfall noted",
                delta=0,
                score_after=score,
                note=f"Shortfall: R{shortfall}. Suggested guarantor income >= R{required_guarantor_income}.",
            )
        )

        reasons.append(f"Bursary does not fully cover rent (shortfall: R{shortfall}).")
        actions.append(
            f"Consider adding a guarantor: target guarantor income >= R{required_guarantor_income}/month "
            f"(so the shortfall stays within 30% affordability)."
        )

    # ==========================================================
    # Upfront cost risk (Informational only: no penalty)
    # ==========================================================
    upfront = rent + deposit + application_fee
    if upfront > effective_income_for_affordability and effective_income_for_affordability > 0:
        breakdown.append(ScoreStep("Upfront cost warning", 0, score, note=f"Upfront = R{upfront}"))
        reasons.append("Upfront cost (rent + deposit + application fee) is high relative to monthly income.")
        actions.append("Ensure deposit/fees are affordable before applying.")

    # ==========================================================
    # Required documents from listing
    # ==========================================================
    missing_required = required_documents - renter_docs
    if missing_required:
        add_step("Missing required listing documents", -18, note=", ".join(sorted(missing_required)))
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
            add_step("Missing recommended docs (cluster)", -6)
            reasons.append("Some recommended documents for your renter category are missing.")
            actions.append("Add the recommended documents to strengthen your application.")

    # ==========================================================
    # Bank statement + payslip logic
    # ==========================================================
    if renter_type == "worker":
        if "payslip" not in renter_docs:
            add_step("Worker missing payslip", -10)
            reasons.append("No payslip provided (income verification is weak).")
            actions.append("Upload your latest payslip(s) to strengthen your application.")

        if "bank_statement" not in renter_docs:
            if "payslip" in renter_docs:
                add_step("Worker missing bank statement", -12)
                reasons.append("No bank statement provided (worker applications usually require it).")
                actions.append("Prepare 3 months bank statements before applying.")
            else:
                add_step("Worker missing bank statement + payslip", -18)
                reasons.append("No bank statement provided and payslip missing (very weak worker documentation).")
                actions.append("Prepare bank statements and payslips before applying.")

    elif renter_type == "new_professional":
        if "bank_statement" not in renter_docs:
            has_strong_np_docs = ("employment_contract" in renter_docs) and ("guarantor_letter" in renter_docs)
            if has_strong_np_docs:
                add_step("New professional missing bank statement (strong docs)", -6)
                reasons.append("No bank statement provided (supporting documents are strong).")
                actions.append("If possible, provide bank statements or alternative proof of income.")
            else:
                add_step("New professional missing bank statement", -10)
                reasons.append("No bank statement provided (may reduce application strength).")
                actions.append("Provide bank statements or supporting proof of income if possible.")

    elif renter_type == "student":
        if non_bursary_student and ("guarantor_bank_statement" not in renter_docs):
            add_step("Student missing guarantor bank statement", -8)
            reasons.append("No guarantor bank statement provided (may weaken application).")
            actions.append("Ask guarantor for 3 months bank statements.")

    # ==========================================================
    # Demand weighting
    # ==========================================================
    if area_demand == "HIGH":
        add_step("High demand area", -10)
        reasons.append("High demand area increases competition.")
        actions.append("Apply only if documents and affordability are strong.")
    elif area_demand == "LOW":
        add_step("Low demand area", +4)
        reasons.append("Lower demand area may reduce competition.")

    # Clamp score
    score = max(0, min(100, score))
    breakdown.append(ScoreStep("Final score clamp", 0, score))

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

    breakdown.append(
        ScoreStep(
            label="Verdict assigned",
            delta=0,
            score_after=score,
            note=f"{verdict} ({confidence})",
        )
    )

    # ==========================================================
    # Application fee logic (Informational only: no score penalty)
    # ==========================================================
    if application_fee >= 800:
        reasons.append("Application fee is high — consider the risk before applying.")
        breakdown.append(ScoreStep("Application fee note", 0, score, note=f"Fee: R{application_fee}"))
    elif application_fee >= 500:
        reasons.append("Application fee is moderate — consider the risk if unsure.")
        breakdown.append(ScoreStep("Application fee note", 0, score, note=f"Fee: R{application_fee}"))

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
        breakdown=breakdown[:30],  # ✅ safety cap for UI
    )

    return result, bands
