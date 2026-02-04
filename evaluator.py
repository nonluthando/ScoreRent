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
    rule_id: str,
    title: str,
    delta: int,
    before: int,
    after: int,
    details: str = "",
) -> None:
    breakdown.append(
        {
            "rule_id": rule_id,
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
    rule_id: str,
    title: str,
    delta: int,
    details: str = "",
) -> int:
    before = int(score)
    raw_after = before + int(delta)
    after = max(0, min(100, raw_after))  # clamp immediately (no clamp breakdown)
    _push_breakdown(breakdown, rule_id, title, int(delta), before, after, details=details)
    return after


def _add_reason(reasons: List[str], text: str) -> None:
    if not _has_item(reasons, text):
        reasons.append(text)


def _add_action(actions: List[str], text: str) -> None:
    if not _has_item(actions, text):
        actions.append(text)


def _trim_output(reasons: List[str], actions: List[str]) -> Tuple[List[str], List[str]]:
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
        "BASE",
        "Base match score",
        0,
        0,
        score,
        "Starts at 100 and adjusts based on affordability, documents, and demand.",
    )

    should_contact_agent = False

    # -----------------------------
    # Affordability
    # -----------------------------
    effective_income = int(monthly_income)

    if non_bursary_student and int(guarantor_monthly_income) > 0:
        effective_income = int(guarantor_monthly_income)

    bands = suggested_budget_bands(int(max(0, effective_income)))
    recommended = bands["recommended"]
    upper_limit = bands["upper_limit"]

    affordability_skip = bursary_student and int(monthly_income) >= int(rent)

    if bursary_student:
        _add_reason(reasons, "Bursary student selected (support considered).")

        if int(monthly_income) >= int(rent):
            score = _apply(score, breakdown, "BURSARY_COVERS", "Bursary/support covers rent", +10)
            _add_reason(reasons, "Your support covers the rent amount.")
        else:
            should_contact_agent = True
            shortfall = int(rent) - int(monthly_income)
            required_guarantor_income = math.ceil(shortfall / 0.30)

            _add_reason(reasons, f"Support does not fully cover rent (shortfall: {_format_currency(shortfall)}).")
            _add_action(
                actions,
                f"Add a guarantor (target income: {_format_currency(required_guarantor_income)} / month).",
            )

    if not affordability_skip:
        pct = _ratio_pct(int(rent), int(effective_income))

        if pct > 40:
            should_contact_agent = True
            score = _apply(
                score,
                breakdown,
                "AFFORDABILITY_ABOVE_40",
                "Affordability risk: rent above 40% of income",
                -70,
                details=f"Rent ratio: {pct:.0f}%",
            )
            _add_reason(reasons, "Rent is too high compared to income (above 40%).")
            _add_action(actions, "Avoid this listing or find a cheaper one.")
        elif pct > 35:
            should_contact_agent = True
            score = _apply(
                score,
                breakdown,
                "AFFORDABILITY_ABOVE_35",
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
                "AFFORDABILITY_ABOVE_30",
                "Affordability warning: rent above 30% recommendation",
                -30,
                details=f"Recommended: {_format_currency(recommended)}",
            )
            _add_reason(reasons, "Rent is slightly high compared to your income (above 30%).")
        else:
            _add_reason(reasons, "Rent is within recommended affordability (30% or less).")

    # -----------------------------
    # Student rules
    # -----------------------------
    if is_student:
        if "proof_of_registration" not in renter_docs_set:
            should_contact_agent = True
            score = _apply(
                score,
                breakdown,
                "STUDENT_MISSING_REG",
                "Student: proof of registration not available",
                -10,
            )
            _add_reason(reasons, "Proof of registration is missing (often normal before Feb registration).")
            _add_action(actions, "Ask if acceptance letter or student number is accepted.")

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
                    "STUDENT_MISSING_GUARANTOR_DOCS",
                    "Missing guarantor documents",
                    -30,
                    details=", ".join(sorted(missing_guarantor_docs)),
                )
                _add_reason(reasons, "Guarantor documents are incomplete for a non-bursary student application.")
                _add_action(actions, "Upload guarantor payslip + bank statement.")

            if int(guarantor_monthly_income) <= 0:
                should_contact_agent = True
                score = _apply(
                    score,
                    breakdown,
                    "STUDENT_MISSING_GUARANTOR_INCOME",
                    "Guarantor income missing",
                    -20,
                )
                _add_reason(reasons, "Guarantor income not provided.")
                _add_action(actions, "Add guarantor monthly income for a correct affordability check.")

    # -----------------------------
    # Required listing documents
    # -----------------------------
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
            "MISSING_REQUIRED_DOCS",
            "Missing listing required documents",
            delta,
            details=", ".join(sorted(missing_required)),
        )
        _add_reason(reasons, "Some documents required by the listing are missing.")
        _add_action(actions, "Gather the missing required documents before paying fees.")

    already_penalised_docs = set(missing_required)

    # -----------------------------
    # Worker rules
    # -----------------------------
    if renter_type == "worker":
        if "payslip" not in renter_docs_set and "payslip" not in already_penalised_docs:
            should_contact_agent = True
            score = _apply(score, breakdown, "WORKER_MISSING_PAYSLIP", "Worker: missing payslip", -20)
            _add_reason(reasons, "Payslip not provided (income verification is weaker).")
            _add_action(actions, "Upload your latest payslip.")

        if "bank_statement" not in renter_docs_set and "bank_statement" not in already_penalised_docs:
            should_contact_agent = True
            score = _apply(score, breakdown, "WORKER_MISSING_BANK", "Worker: missing bank statement", -25)
            _add_reason(reasons, "Bank statement not provided (often required).")
            _add_action(actions, "Prepare 3 months bank statements.")

    # -----------------------------
    # New professional rules
    # -----------------------------
    if renter_type == "new_professional":
        if has_employment_contract:
            score = _apply(score, breakdown, "NEWPRO_CONTRACT", "Employment contract provided", +8)
            _add_reason(reasons, "Employment contract provided (strong proof of income).")

        if has_guarantor_letter:
            score = _apply(score, breakdown, "NEWPRO_GUARANTOR_LETTER", "Guarantor letter provided", +5)
            _add_reason(reasons, "Guarantor letter provided (support signal).")

    # -----------------------------
    # Demand
    # -----------------------------
    if area_demand == "HIGH":
        should_contact_agent = True
        score = _apply(score, breakdown, "DEMAND_HIGH", "High demand area", -10)
        _add_reason(reasons, "High demand area means more competition.")
    elif area_demand == "LOW":
        score = _apply(score, breakdown, "DEMAND_LOW", "Low demand area", +5)
        _add_reason(reasons, "Lower demand area may reduce competition.")

    # -----------------------------
    # Fees + upfront
    # -----------------------------
    upfront = int(rent) + int(deposit) + int(application_fee)

    if int(application_fee) >= 800:
        should_contact_agent = True
        _add_reason(reasons, "Application fee is high.")
    elif int(application_fee) >= 500:
        should_contact_agent = True
        _add_reason(reasons, "Application fee is moderate.")

    if effective_income > 0 and upfront > effective_income:
        should_contact_agent = True
        _add_reason(reasons, "Upfront cost (rent + deposit + fee) is high compared to income.")
        _add_action(actions, "Double-check fees and deposit affordability.")

    if should_contact_agent:
        _add_action(actions, "Contact the agent to confirm requirements before paying fees.")

    # -----------------------------
    # Verdict
    # -----------------------------
    if score >= 75:
        verdict = "WORTH_APPLYING"
        confidence = "HIGH"
    elif score >= 55:
        verdict = "BORDERLINE"
        confidence = "MEDIUM"
    else:
        verdict = "NOT_WORTH_IT"
        confidence = "LOW"

    _push_breakdown(breakdown, "VERDICT", "Verdict assigned", 0, score, score, f"{verdict} ({confidence})")

    if confidence == "HIGH":
        _add_action(actions, "Apply. This looks like a strong match.")
    elif confidence == "MEDIUM":
        rent_above_recommended = any(b.get("rule_id") == "AFFORDABILITY_ABOVE_30" for b in breakdown)
        if rent_above_recommended:
            _add_action(actions, "If possible, consider roommates/house-sharing to reduce rent.")
        _add_action(actions, "Improve docs or affordability before applying.")
    else:
        _add_action(actions, "Avoid unless affordability or documentation improves.")

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
