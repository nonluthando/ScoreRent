import pytest
from evaluator import evaluate, suggested_budget_bands


# ------------------------------------------------------------
# BASIC SANITY TEST
# ------------------------------------------------------------

def test_returns_valid_result_object():

    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.score >= 0
    assert result.score <= 100
    assert result.verdict in ["WORTH_APPLYING", "BORDERLINE", "NOT_WORTH_IT"]
    assert result.confidence in ["HIGH", "MEDIUM", "LOW"]
    assert isinstance(result.reasons, list)
    assert isinstance(result.actions, list)
    assert isinstance(result.breakdown, list)


# ------------------------------------------------------------
# AFFORDABILITY TESTS
# ------------------------------------------------------------

def test_high_affordability_is_high_confidence():

    result, _ = evaluate(
        renter_type="worker",
        monthly_income=30000,
        renter_docs=["bank_statement", "payslip"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert result.confidence == "HIGH"
    assert result.verdict == "WORTH_APPLYING"


def test_extreme_affordability_failure():

    result, _ = evaluate(
        renter_type="worker",
        monthly_income=10000,
        renter_docs=["bank_statement", "payslip"],
        rent=6000,  # 60%
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.confidence == "LOW"
    assert result.verdict == "NOT_WORTH_IT"


# ------------------------------------------------------------
# BUDGET BAND TEST
# ------------------------------------------------------------

def test_budget_band_calculation():

    bands = suggested_budget_bands(20000)

    assert bands["conservative"] == 5000
    assert bands["recommended"] == int(20000 * 0.33)
    assert bands["upper_limit"] == int(20000 * 0.38)


# ------------------------------------------------------------
# DOCUMENT PENALTY TEST
# ------------------------------------------------------------

def test_missing_required_documents_penalty():

    result, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=[],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="MEDIUM",
    )

    assert result.score < 100
    assert any("missing" in r.lower() for r in result.reasons)


# ------------------------------------------------------------
# DEMAND TESTS
# ------------------------------------------------------------

def test_high_demand_penalty():

    high_demand, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="HIGH",
    )

    low_demand, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert high_demand.score < low_demand.score


# ------------------------------------------------------------
# BURSARY STUDENT TESTS
# ------------------------------------------------------------

def test_bursary_student_with_full_cover():

    result, _ = evaluate(
        renter_type="student",
        monthly_income=9000,
        renter_docs=["bursary letter"],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        is_bursary_student=True,
    )

    assert result.score > 70
    assert result.verdict in ["WORTH_APPLYING", "BORDERLINE"]


def test_bursary_student_missing_bursary_letter_penalty():

    result, _ = evaluate(
        renter_type="student",
        monthly_income=9000,
        renter_docs=[],  # missing bursary proof
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        is_bursary_student=True,
    )

    assert result.score < 100
    assert any("bursary" in r.lower() for r in result.reasons)


def test_bursary_shortfall_penalty():

    result, _ = evaluate(
        renter_type="student",
        monthly_income=4000,
        renter_docs=["bursary letter"],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        is_bursary_student=True,
    )

    assert result.score < 70
    assert any("guarantor" in a.lower() for a in result.actions)


# ------------------------------------------------------------
# GUARANTOR TEST
# ------------------------------------------------------------

def test_guarantor_improves_score():

    without, _ = evaluate(
        renter_type="student",
        monthly_income=4000,
        renter_docs=["bursary letter"],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=0,
        is_bursary_student=True,
    )

    with_guarantor, _ = evaluate(
        renter_type="student",
        monthly_income=4000,
        renter_docs=["bursary letter"],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=30000,
        is_bursary_student=True,
    )

    assert with_guarantor.score > without.score


# ------------------------------------------------------------
# CONFIDENCE LEVEL TESTS
# ------------------------------------------------------------

def test_high_confidence_verdict():

    result, _ = evaluate(
        renter_type="worker",
        monthly_income=40000,
        renter_docs=["bank_statement", "payslip"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert result.confidence == "HIGH"
    assert result.verdict == "WORTH_APPLYING"


def test_borderline_confidence():

    result, _ = evaluate(
        renter_type="worker",
        monthly_income=18000,
        renter_docs=["bank_statement", "payslip"],
        rent=6500,
        deposit=6500,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.confidence in ["MEDIUM", "HIGH", "LOW"]


# ------------------------------------------------------------
# SCORE CLAMP TEST
# ------------------------------------------------------------

def test_score_never_exceeds_bounds():

    result, _ = evaluate(
        renter_type="student",
        monthly_income=100000,
        renter_docs=["bursary letter"],
        rent=1000,
        deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
        is_bursary_student=True,
    )

    assert 0 <= result.score <= 100
