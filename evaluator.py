import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


# ------------------------------------------------------------
# Market configuration (Cape Town only)
# ------------------------------------------------------------

APP_MARKET = "Cape Town"

CURRENCY_CODE = "ZAR"
CURRENCY_SYMBOL = "R"

# Cape Town calibrated affordability thresholds
CAPE_TOWN_RECOMMENDED_CAP = 0.33
CAPE_TOWN_UPPER_CAP = 0.38
CAPE_TOWN_EXTREME_CAP = 0.45


# ------------------------------------------------------------
# Result object
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Money helpers
# ------------------------------------------------------------

def _money(value: Any) -> int:
    try:
        return max(0, int(round(float(value))))
    except:
        return 0


def _format_currency(value: int) -> str:
    value = _money(value)
    return f"{CURRENCY_SYMBOL}{value:,}".replace(",", " ")


# ------------------------------------------------------------
# Budget bands (Cape Town calibrated)
# ------------------------------------------------------------

def suggested_budget_bands(monthly_income: int) -> Dict[str, int]:

    monthly_income = _money(monthly_income)

    return {
        "conservative": int(monthly_income * 0.25),
        "recommended": int(monthly_income * CAPE_TOWN_RECOMMENDED_CAP),
        "upper_limit": int(monthly_income * CAPE_TOWN_UPPER_CAP),
    }


# ------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------

def _dedupe_keep_order(items: List[str]) -> List[str]:
    return list(dict.fromkeys(items))


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
    after = score + int(delta)

    _push_breakdown(
        breakdown,
        title,
        delta,
        before,
        after,
        details,
    )

    return after


def _add_reason(reasons: List[str], text: str) -> None:
    if not _has_item(reasons, text):
        reasons.append(text)


def _add_action(actions: List[str], text: str) -> None:
    if not _has_item(actions, text):
        actions.append(text)


def _trim_output(
    reasons: List[str],
    actions: List[str],
) -> Tuple[List[str], List[str]]:

    reasons = _dedupe_keep_order(reasons)[:5]
    actions = _dedupe_keep_order(actions)[:4]

    return reasons, actions


# ------------------------------------------------------------
# Main evaluator
# ------------------------------------------------------------

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

    # Normalize money inputs
    monthly_income = _money(monthly_income)
    rent = _money(rent)
    deposit = _money(deposit)
    application_fee = _money(application_fee)
    guarantor_monthly_income = _money(guarantor_monthly_income)

    reasons: List[str] = []
    actions: List[str] = []
    breakdown: List[Dict[str, Any]] = []

    renter_type = (renter_type or "").strip().lower()

    if renter_type not in RENTER_TYPES:
        renter_type = "worker"

    renter_docs_set = set(d.strip().lower() for d in (renter_docs or []))
    required_docs_set = set(d.strip().lower() for d in (required_documents or []))

    area_demand = (area_demand or "MEDIUM").upper()

    if area_demand not in DEMAND_LEVELS:
        area_demand = "MEDIUM"

    is_student = renter_type == "student"
    bursary_student = is_student and is_bursary_student
    non_bursary_student = is_student and not is_bursary_student

    score = 100

    _push_breakdown(
        breakdown,
        "Base match score",
        0,
        0,
        score,
        f"Evaluation calibrated for {APP_MARKET} rental market (2026).",
    )

    # ------------------------------------------------------------
    # Determine effective income
    # ------------------------------------------------------------

    effective_income = monthly_income

    if non_bursary_student and guarantor_monthly_income > 0:
        effective_income = guarantor_monthly_income

    bands = suggested_budget_bands(effective_income)

    # ------------------------------------------------------------
    # Bursary affordability logic (Cape Town 2026 realistic)
    # ------------------------------------------------------------

    affordability_skip = False

    if bursary_student:

        affordability_skip = True

        # 1. Proof of bursary required — big hit if missing
        bursary_doc_terms = ["bursary letter", "bursary confirmation", "award letter", "nsfas", "bursary agreement"]
        has_bursary_proof = any(any(term in doc for term in bursary_doc_terms) for doc in renter_docs_set)

        if not has_bursary_proof:
            score = _apply(
                score,
                breakdown,
                "Missing official bursary confirmation letter",
                -35,
                "Landlords/agencies almost always require this"
            )
            _add_reason(reasons, "Official bursary award letter is missing.")
            _add_action(actions, "Upload bursary confirmation letter / NSFAS award letter.")

        # 2. Coverage + buffer assessment
        covers_rent = monthly_income >= rent
        living_buffer = monthly_income - rent   # leftover after rent
        shortfall = max(0, rent - monthly_income)

        if covers_rent:
            if living_buffer >= 4000:  # decent buffer for food/utilities/transport (2026 CT reality)
                score = _apply(
                    score,
                    breakdown,
                    "Bursary covers rent + strong living buffer",
                    +28,
                    f"Buffer: {_format_currency(living_buffer)}"
                )
                _add_reason(reasons, "Bursary fully covers rent with good buffer for living costs.")
            elif living_buffer >= 1500:  # marginal buffer — still acceptable to many
                score = _apply(
                    score,
                    breakdown,
                    "Bursary covers rent + modest living buffer",
                    +12,
                    f"Buffer: {_format_currency(living_buffer)}"
                )
                _add_reason(reasons, "Bursary covers rent but living costs will be tight.")
            else:  # barely covers rent — risky
                score = _apply(
                    score,
                    breakdown,
                    "Bursary covers rent but very tight/no buffer",
                    -8,
                    "Minimal buffer for food/utilities"
                )
                _add_reason(reasons, "Bursary covers rent exactly — little room for other expenses.")
        else:
            # Shortfall logic — harsher than original
            if shortfall <= 800:
                score = _apply(
                    score,
                    breakdown,
                    "Small bursary shortfall",
                    -18,
                    f"Shortfall: {_format_currency(shortfall)}"
                )
            elif shortfall <= 2000:
                score = _apply(
                    score,
                    breakdown,
                    "Moderate bursary shortfall",
                    -38,
                    f"Shortfall: {_format_currency(shortfall)}"
                )
            else:
                score = _apply(
                    score,
                    breakdown,
                    "Large bursary shortfall",
                    -65,
                    f"Shortfall: {_format_currency(shortfall)}"
                )
                _add_reason(reasons, "Bursary falls well short of rent — high risk without strong guarantor.")

            _add_action(actions, "Consider properties within bursary allowance or add guarantor.")

        # 3. Guarantor still very important (even with bursary)
        if guarantor_monthly_income > 0:
            guar_ratio = _ratio_pct(rent, guarantor_monthly_income)
            if guar_ratio <= 25:  # guarantor very strong
                score = _apply(
                    score,
                    breakdown,
                    "Very strong guarantor backup",
                    +22,
                    f"Guarantor rent ratio: {guar_ratio:.0f}%"
                )
            elif guar_ratio <= 40:
                score = _apply(
                    score,
                    breakdown,
                    "Solid guarantor present",
                    +10,
                    f"Guarantor rent ratio: {guar_ratio:.0f}%"
                )
            else:
                score = _apply(
                    score,
                    breakdown,
                    "Guarantor present but stretched",
                    -5,
                    f"Guarantor rent ratio: {guar_ratio:.0f}%"
                )

    # ------------------------------------------------------------
    # Normal affordability logic (non-bursary or fallback)
    # ------------------------------------------------------------

    if not affordability_skip:

        pct = _ratio_pct(rent, effective_income)

        if pct > CAPE_TOWN_EXTREME_CAP * 100:
            score = _apply(
                score,
                breakdown,
                "Affordability risk: far above Cape Town approval range",
                -70,
                f"{pct:.0f}% of income",
            )
            _add_reason(
                reasons,
                "Rent is far above typical approval range for Cape Town.",
            )

        elif pct > CAPE_TOWN_UPPER_CAP * 100:
            score = _apply(
                score,
                breakdown,
                "Affordability risk: above Cape Town approval range",
                -50,
                f"{pct:.0f}% of income",
            )
            _add_reason(
                reasons,
                "Rent exceeds common approval affordability in Cape Town.",
            )

        elif pct > CAPE_TOWN_RECOMMENDED_CAP * 100:
            score = _apply(
                score,
                breakdown,
                "Affordability warning",
                -25,
                f"{pct:.0f}% of income",
            )
            _add_reason(
                reasons,
                "Rent is slightly high relative to income.",
            )

        else:
            _add_reason(
                reasons,
                "Rent is within safe approval range for Cape Town.",
            )

    # ------------------------------------------------------------
    # Required documents (unchanged)
    # ------------------------------------------------------------

    missing_required = required_docs_set - renter_docs_set

    if missing_required:

        score = _apply(
            score,
            breakdown,
            "Missing required documents",
            -20,
            ", ".join(missing_required),
        )

        _add_reason(
            reasons,
            "Some required documents are missing.",
        )

        _add_action(
            actions,
            "Prepare all required documents before applying.",
        )

    # ------------------------------------------------------------
    # Demand adjustment (unchanged)
    # ------------------------------------------------------------

    if area_demand == "HIGH":

        score = _apply(
            score,
            breakdown,
            "High demand area",
            -10,
        )

        _add_reason(
            reasons,
            "Competition is high in this Cape Town area.",
        )

    elif area_demand == "LOW":

        score = _apply(
            score,
            breakdown,
            "Low demand area",
            +5,
        )

    # ------------------------------------------------------------
    # Upfront cost warning (unchanged)
    # ------------------------------------------------------------

    upfront = rent + deposit + application_fee

    if effective_income > 0 and upfront > effective_income:

        _add_reason(
            reasons,
            "Upfront costs are high relative to income.",
        )

        _add_action(
            actions,
            "Ensure deposit and upfront costs are affordable.",
        )

    # ------------------------------------------------------------
    # Clamp score and assign verdict
    # ------------------------------------------------------------

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

    _push_breakdown(
        breakdown,
        "Final verdict",
        0,
        score,
        score,
        f"{verdict} ({confidence})",
    )

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
