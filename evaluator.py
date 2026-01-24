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


def evaluate(
    renter_type: str,
    monthly_income: int,
    renter_docs: List[str],
    rent: int,
    deposit: int,
    application_fee: int,
    required_documents: List[str],
    area_demand: str,
) -> Tuple[EvaluationResult, Dict[str, int]]:
    reasons = []
    actions = []
    score = 70

    renter_docs = set([d.strip().lower() for d in renter_docs if d.strip()])
    required_documents = set([d.strip().lower() for d in required_documents if d.strip()])
    area_demand = area_demand.upper().strip() if area_demand else "MEDIUM"

    bands = suggested_budget_bands(monthly_income)
    upper_limit = bands["upper_limit"]
    recommended = bands["recommended"]

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

    upfront = rent + deposit + application_fee
    if upfront > monthly_income:
        score -= 10
        reasons.append("Upfront cost (rent + deposit + application fee) is high relative to monthly income.")
        actions.append("Ensure deposit/fees are affordable before applying.")

    missing_required = required_documents - renter_docs
    if missing_required:
        score -= 18
        reasons.append("Some required documents are missing.")
        actions.append("Gather the missing required documents before applying.")

    cluster_docs = DOC_CLUSTERS.get(renter_type, set())
    missing_cluster = cluster_docs - renter_docs
    if missing_cluster and len(missing_cluster) < len(cluster_docs):
        score -= 6
        reasons.append("Some recommended documents for your renter category are missing.")
        actions.append("Add the recommended documents to strengthen your application.")

    if "bank_statement" not in renter_docs:
        score -= 14
        reasons.append("No bank statement provided (may reduce application strength).")
        actions.append("Prepare 3 months bank statements if available.")

    if application_fee >= 800:
        score -= 8
        reasons.append("High application fee increases cost of a low-confidence application.")
        actions.append("Avoid high-fee applications unless score is strong.")
    elif application_fee >= 500:
        score -= 4
        reasons.append("Moderate application fee increases risk if application is weak.")

    if area_demand == "HIGH":
        score -= 10
        reasons.append("High demand area increases competition.")
        actions.append("Apply only if documents and affordability are strong.")
    elif area_demand == "LOW":
        score += 4
        reasons.append("Lower demand area may reduce competition.")

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

    actions = list(dict.fromkeys(actions))[:5]
    reasons = list(dict.fromkeys(reasons))[:8]

    return EvaluationResult(score, verdict, confidence, reasons, actions), bands
