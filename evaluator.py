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


RENTER_TYPES = ["worker", "new_professional", "student"]
DEMAND_LEVELS = ["LOW", "MEDIUM", "HIGH"]


def suggested_budget_bands(monthly_income: int) -> Dict[str, int]:
    return {
        "conservative": int(monthly_income * 0.25),
        "recommended": int(monthly_income * 0.30),
        "upper_limit": int(monthly_income * 0.35),
    }


def _dedupe(items: List[str]) -> List[str]:
    return list(dict.fromkeys(items))


def _format_currency(value: int) -> str:
    return f"R{int(value):,}".replace(",", " ")


def _ratio_pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 999.0
    return (numerator / denominator) * 100.0


def _push_breakdown(breakdown, title, delta, before, after, details=""):
    breakdown.append(
        {
            "title": title,
            "delta": delta,
            "before": before,
            "after": after,
            "details": details,
        }
    )


def _apply(score, breakdown, title, delta, details=""):
    before = score
    after = score + delta
    _push_breakdown(breakdown, title, delta, before, after, details)
    return after


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

    renter_type = renter_type if renter_type in RENTER_TYPES else "worker"
    area_demand = area_demand if area_demand in DEMAND_LEVELS else "MEDIUM"

    renter_docs = set(renter_docs or [])
    required_docs = set(required_documents or [])

    score = 100
    _push_breakdown(
        breakdown,
        "Base match score",
        0,
        0,
        score,
        "Starting point before adjustments",
    )

    effective_income = guarantor_monthly_income if renter_type == "student" and guarantor_monthly_income > 0 else monthly_income
    bands = suggested_budget_bands(max(0, effective_income))

    if effective_income > 0:
        pct = _ratio_pct(rent, effective_income)

        if pct > 40:
            score = _apply(score, breakdown, "Rent exceeds 40 percent of income", -70)
            reasons.append("Rent is extremely high compared to income.")
        elif pct > 35:
            score = _apply(score, breakdown, "Rent exceeds 35 percent limit", -50)
            reasons.append("Rent exceeds safe affordability limits.")
        elif pct > 30:
            score = _apply(score, breakdown, "Rent exceeds recommended 30 percent", -30)
            reasons.append("Rent is slightly high relative to income.")
        else:
            reasons.append("Rent is within recommended affordability.")

    missing_required = required_docs - renter_docs
    if missing_required:
        penalty = -15 if len(missing_required) == 1 else -25 if len(missing_required) == 2 else -30
        score = _apply(
            score,
            breakdown,
            "Missing required listing documents",
            penalty,
            ", ".join(sorted(missing_required)),
        )
        reasons.append("Some required listing documents are missing.")

    if area_demand == "HIGH":
        score = _apply(score, breakdown, "High demand area", -10)
        reasons.append("High demand increases competition.")

    score = max(0, min(100, score))

    if score >= 75:
        verdict = "WORTH_APPLYING"
        confidence = "HIGH"
        actions.append("You can apply with confidence.")
    elif score >= 55:
        verdict = "BORDERLINE"
        confidence = "MEDIUM"
        actions.append("Proceed carefully before applying.")
        actions.append("Confirm requirements with the agent before paying any fees.")
    else:
        verdict = "NOT_WORTH_IT"
        confidence = "LOW"
        actions.append("Avoid applying unless key issues can be resolved.")

    _push_breakdown(
        breakdown,
        "Final verdict",
        0,
        score,
        score,
        f"{verdict} confidence",
    )

    return (
        EvaluationResult(
            score=score,
            verdict=verdict,
            confidence=confidence,
            reasons=_dedupe(reasons)[:5],
            actions=_dedupe(actions)[:4],
            breakdown=breakdown,
        ),
        bands,
    )
