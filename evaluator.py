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


def _add_reason(reasons: List[str], text: str) -> None:
    if not _has_item(reasons, text):
        reasons.append(text)


def _add_action(actions: List[str], text: str) -> None:
    if not _has_item(actions, text):
        actions.append(text)


def _trim_output(reasons: List[str], actions: List[str]) -> Tuple[List[str], List[str]]:
    # Product-style output: short and useful
    reasons = _dedupe_keep_order(reasons)[:5]
    actions = _dedupe_keep_order(actions)[:4]
    return reasons, actions


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
        "Base match score",
        0,
        0,
        score,
        "Starts at 100 and adjusts based on affordability, documents, and demand.",
    )

    # This flag controls if we suggest calling/confirming with agent
    should_contact_agent = False

    # ------------------------------------------------------------
    # Affordability
    # ------------------------------------------------------------
    effective_income = int(monthly_income)

    # For non-bursary students, affordability is based on guarantor if provided
    if non_bursary_student and int(guarantor_monthly_income) > 0:
        effective_income = int(guarantor_monthly_income)

    bands = suggested_budget_bands(int(max(0, effective_income)))
    recommended = bands["recommended"]
    upper_limit = bands["upper_limit"]

    # Bursary: if bursary/support covers rent, skip affordability penalties entirely
    affordability_skip = bursary_student and int(monthly_income) >= int(rent)

    if bursary_student:
        _add_reason(reasons, "You selected bursary student (support considered in affordability).")

        if int(monthly_income) >= int(rent):
            score = _apply(score, breakdown, "Bursary/support covers rent", +10)
            _add_reason(reasons, "Your support covers the rent amount.")
            _add_action(actions, "You can apply with confidence.")
        else:
            should_contact_agent = True
            shortfall = int(rent) - int(monthly_income)
            required_guarantor_income = math.ceil(shortfall / 0.30)
            _add_reason(reasons, f"Support does not fully cover rent (shortfall: {_format_currency(shortfall)}).")
            _add_action(
                actions,
                f"Consider adding a guarantor (target income: {_format_currency(required_guarantor_income)} per month).",
            )

    if not affordability_skip:
        pct = _ratio_pct(int(rent), int(effective_income))

        if pct > 40:
            should_contact_agent = True
            score = _apply(
                score,
                breakdown,
                "Affordability risk: rent above 40% of income",
                -70,
                details=f"Rent ratio: {pct:.0f}%",
            )
            _add_reason(reasons, "Rent is too high compared to income (above 40%).")
            _add_action(actions, "Avoid this listing or look for a cheaper one.")
        elif pct > 35:
            should_contact_agent = True
            score = _apply(
                score,
                breakdown,
                "Affordability risk: rent above 35% limit",
                -50,
                details=f"Upper limit: {_format_currency(upper_limit)}",
            )
            _add_reason(reasons, "Rent is above the safe affordability limit (35%).")
            _add_action(actions, "Avoid or negotiate rent closer to your budget.")
        elif pct > 30:
            should_contact_agent = True
            score = _apply(
                score,
                breakdown,
                "Affordability warning: rent above 30% recommendation",
                -30,
                details=f"Recommended: {_format_currency(recommended)}",
            )
            _add_reason(reasons, "Rent is slightly high compared to your income (above 30%).")
            _add_action(actions, "Proceed carefully and confirm total costs before paying fees.")
        else:
            _add_reason(reasons, "Rent is within recommended affordability (30% or less).")

    # ------------------------------------------------------------
    # Student-specific logic
    # ------------------------------------------------------------
    if is_student:
        # Softer, realistic rule
        if "proof_of_registration" not in renter_docs_set:
            should_contact_agent = True
            score = _apply(score, breakdown, "Student: proof of registration not available", -10)
            _add_reason(
                reasons,
                "Proof of registration is missing (this can be normal before February registration).",
            )
            _add_action(actions, "Ask if the landlord accepts an acceptance letter or student number instead.")

        if non_bursary_student:
            required_guarantor_docs = {
                "guarantor_letter",
                "guarantor_payslip",
                "guarantor_bank_statement",
            }

            missing_guarantor_docs = required_guarantor_docs - renter_docs_set
            if missing_guarantor_docs:
                should_contact_agent = True
                score = _apply(
                    score,
                    breakdown,
                    "Missing guarantor documents",
                    -30,
                    details=", ".join(sorted(missing_guarantor_docs)),
                )
                _add_reason(reasons, "Guarantor documents are incomplete for a non-bursary student application.")
                _add_action(actions, "Add guarantor payslip and bank statement before applying.")

            if int(guarantor_monthly_income) <= 0:
                should_contact_agent = True
                score = _apply(score, breakdown, "Guarantor income missing", -20)
                _add_reason(reasons, "Guarantor income was not provided.")
                _add_action(actions, "Add guarantor monthly income so ScoreRent can assess affordability correctly.")

    # ------------------------------------------------------------
    # Listing required documents
    # ------------------------------------------------------------
    missing_required = required_docs_set - renter_docs_set
    if missing_required:
        should_contact_agent = True
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
            "Missing listing required documents",
            delta,
            details=", ".join(sorted(missing_required)),
        )
        _add_reason(reasons, "Some documents required by the listing are missing.")
        _add_action(actions, "Gather the missing documents before paying the application fee.")

    already_penalised_docs = set(missing_required)

    # ------------------------------------------------------------
    # Worker rules
    # ------------------------------------------------------------
    if renter_type == "worker":
        if "payslip" not in renter_docs_set and "payslip" not in already_penalised_docs:
            should_contact_agent = True
            score = _apply(score, breakdown, "Worker: missing payslip", -20)
            _add_reason(reasons, "Payslip not provided (income verification is weaker).")
            _add_action(actions, "Upload your latest payslip.")

        if "bank_statement" not in renter_docs_set and "bank_statement" not in already_penalised_docs:
            should_contact_agent = True
            if "payslip" in renter_docs_set:
                score = _apply(score, breakdown, "Worker: missing bank statement", -25)
                _add_reason(reasons, "Bank statement not provided (often required).")
                _add_action(actions, "Prepare 3 months of bank statements.")
            else:
                score = _apply(score, breakdown, "Worker: missing bank statement and payslip", -35)
                _add_reason(reasons, "Missing bank statement and payslip.")
                _add_action(actions, "Prepare bank statements and payslips before applying.")

    # ------------------------------------------------------------
    # New professional rules
    # ------------------------------------------------------------
    if renter_type == "new_professional":
        if has_employment_contract:
            score = _apply(score, breakdown, "Employment contract provided", +8)
            _add_reason(reasons, "Employment contract provided (strong support for income).")

        if has_guarantor_letter:
            score = _apply(score, breakdown, "Guarantor letter provided", +5)
            _add_reason(reasons, "Guarantor letter provided (adds support).")

        if "bank_statement" not in renter_docs_set and "bank_statement" not in already_penalised_docs:
            should_contact_agent = True
            if not has_employment_contract:
                score = _apply(score, breakdown, "New professional: missing bank statement", -10)
                _add_reason(reasons, "Bank statement not provided.")
                _add_action(actions, "Add a bank statement or alternative proof of income.")
            else:
                score = _apply(score, breakdown, "New professional: missing bank statement (contract present)", -4)

        if "payslip" not in renter_docs_set and "payslip" not in already_penalised_docs:
            should_contact_agent = True
            if not has_employment_contract:
                score = _apply(score, breakdown, "New professional: missing payslip", -8)
                _add_reason(reasons, "Payslip not provided.")
                _add_action(actions, "Provide a payslip or employment contract.")
            else:
                score = _apply(score, breakdown, "New professional: missing payslip (contract present)", -3)

    # ------------------------------------------------------------
    # Demand
    # ------------------------------------------------------------
    if area_demand == "HIGH":
        should_contact_agent = True
        score = _apply(score, breakdown, "High demand area", -10)
        _add_reason(reasons, "High demand area means more competition.")
        _add_action(actions, "Apply only if your docs are strong.")
    elif area_demand == "LOW":
        score = _apply(score, breakdown, "Low demand area", +5)
        _add_reason(reasons, "Lower demand area may reduce competition.")

    # ------------------------------------------------------------
    # Fees and upfront cost
    # ------------------------------------------------------------
    upfront = int(rent) + int(deposit) + int(application_fee)

    if int(application_fee) >= 800:
        should_contact_agent = True
        _add_reason(reasons, "Application fee is high.")
        _add_action(actions, "Confirm requirements with the agent before paying.")
    elif int(application_fee) >= 500:
        should_contact_agent = True
        _add_reason(reasons, "Application fee is moderate.")
        _add_action(actions, "Confirm requirements before paying if you are unsure.")

    if effective_income > 0 and upfront > effective_income:
        should_contact_agent = True
        _add_reason(reasons, "Upfront cost (rent + deposit + fee) is high compared to your income.")
        _add_action(actions, "Make sure you can afford the deposit and fees before applying.")

    # Suggest contacting agent only when needed
    if should_contact_agent:
        _add_action(actions, "Contact the agent to confirm the exact requirements before paying any fees.")

    # ------------------------------------------------------------
    # Clamp + verdict
    # ------------------------------------------------------------
    before = score
    score = max(0, min(100, int(score)))
    if score != before:
        _push_breakdown(breakdown, "Final score clamp", 0, before, score)

    if score >= 75:
        verdict = "WORTH_APPLYING"
        confidence = "HIGH"
    elif score >= 55:
        verdict = "BORDERLINE"
        confidence = "MEDIUM"
    else:
        verdict = "NOT_WORTH_IT"
        confidence = "LOW"

    _push_breakdown(breakdown, "Verdict assigned", 0, score, score, f"{verdict} ({confidence})")

    # Make the top action feel like the app is talking
    if confidence == "HIGH":
        _add_action(actions, "You can apply. This looks like a strong match.")
    elif confidence == "MEDIUM":
    rent_above_recommended = any(
        "affordability: rent above recommended" in (b.get("title", "").lower())
        for b in breakdown
    )

    if rent_above_recommended:
        actions.append("Consider roommates/house-sharing to reduce rent burden.")

    actions.append("Improve docs or affordability before applying.")
    else:
        _add_action(actions, "Avoid unless you can fix the missing requirements and affordability.")

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
        bands,
    )
