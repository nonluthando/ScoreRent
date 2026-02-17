from evaluator import evaluate


# ------------------------------------------------------------
# Affordability tests
# ------------------------------------------------------------

def test_affordability_penalty_when_rent_exceeds_upper_limit():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=9000,  # 45%
        deposit=9000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert result.score < 100

    assert any(
        "exceeds common approval affordability" in r.lower()
        or "far above typical approval range" in r.lower()
        for r in result.reasons
    )


def test_affordability_safe_range():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement"],
        rent=6000,  # 30%
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.score >= 75

    assert any(
        "safe approval range" in r.lower()
        for r in result.reasons
    )


def test_affordability_warning_range():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement"],
        rent=7000,  # 35%
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.score < 100


# ------------------------------------------------------------
# Bursary student tests
# ------------------------------------------------------------

def test_bursary_student_fully_covers_rent():
    result, bands = evaluate(
        renter_type="student",
        monthly_income=8000,
        renter_docs=["bursary_letter"],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        is_bursary_student=True,
    )

    assert result.score >= 90

    assert any(
        "bursary fully covers" in r.lower()
        for r in result.reasons
    )


def test_bursary_student_shortfall():
    result, bands = evaluate(
        renter_type="student",
        monthly_income=5000,
        renter_docs=["bursary_letter"],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        is_bursary_student=True,
    )

    assert result.score < 100

    assert any(
        "does not fully cover" in r.lower()
        for r in result.reasons
    )

    assert any(
        "guarantor" in a.lower()
        for a in result.actions
    )


# ------------------------------------------------------------
# Guarantor income tests
# ------------------------------------------------------------

def test_non_bursary_student_uses_guarantor_income():
    result, bands = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=["guarantor_letter"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
        guarantor_monthly_income=20000,
        is_bursary_student=False,
    )

    assert result.score >= 75

    assert bands["recommended"] == int(20000 * 0.33)


def test_non_bursary_student_no_guarantor_income_is_risky():
    result, bands = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=["guarantor_letter"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=0,
        is_bursary_student=False,
    )

    assert result.score <= 50


# ------------------------------------------------------------
# Required document tests
# ------------------------------------------------------------

def test_missing_required_documents_penalty():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["payslip"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="MEDIUM",
    )

    assert result.score < 100

    assert any(
        "required documents" in r.lower()
        for r in result.reasons
    )


def test_all_required_documents_present():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="MEDIUM",
    )

    assert result.score >= 75


# ------------------------------------------------------------
# Demand tests
# ------------------------------------------------------------

def test_high_demand_penalty():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="HIGH",
    )

    assert result.score < 100

    assert any(
        "competition is high" in r.lower()
        for r in result.reasons
    )


def test_low_demand_bonus():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert result.score >= 95


# ------------------------------------------------------------
# Upfront cost tests
# ------------------------------------------------------------

def test_upfront_cost_warning():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=10000,
        renter_docs=["bank_statement"],
        rent=6000,
        deposit=6000,
        application_fee=1000,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert any(
        "upfront costs" in r.lower()
        for r in result.reasons
    )


# ------------------------------------------------------------
# Verdict and confidence tests
# ------------------------------------------------------------

def test_high_confidence_verdict():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=30000,
        renter_docs=["bank_statement"],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert result.verdict == "WORTH_APPLYING"

    assert result.confidence == "HIGH"


def test_valid_verdict_values():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=10000,
        renter_docs=["bank_statement"],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="HIGH",
    )

    assert result.verdict in [
        "WORTH_APPLYING",
        "BORDERLINE",
        "NOT_WORTH_IT",
    ]

    assert result.confidence in [
        "HIGH",
        "MEDIUM",
        "LOW",
    ]


# ------------------------------------------------------------
# Budget band tests
# ------------------------------------------------------------

def test_budget_band_calculation():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert bands["recommended"] == int(20000 * 0.33)

    assert bands["upper_limit"] == int(20000 * 0.38)

    assert bands["conservative"] == int(20000 * 0.25)
