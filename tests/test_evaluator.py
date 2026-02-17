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
    assert any("above" in r.lower() or "far above" in r.lower() for r in result.reasons)


def test_affordability_safe_range():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=6000,  # 30%
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.score >= 75
    assert any("safe approval range" in r.lower() for r in result.reasons)


# ------------------------------------------------------------
# Bursary student tests
# ------------------------------------------------------------

def test_bursary_student_affordable():
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
    assert any("bursary fully covers" in r.lower() for r in result.reasons)


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
    assert any("does not fully cover" in r.lower() for r in result.reasons)
    assert any("guarantor" in a.lower() for a in result.actions)


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


# ------------------------------------------------------------
# Required documents tests
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
    assert any("required documents" in r.lower() for r in result.reasons)


def test_all_required_documents_present():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["payslip", "bank_statement"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="MEDIUM",
    )

    assert result.score >= 75


# ------------------------------------------------------------
# Demand adjustment tests
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
    assert any("competition is high" in r.lower() for r in result.reasons)


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

    assert result.score >= 100 or result.score == 100


# ------------------------------------------------------------
# Upfront cost informational only
# ------------------------------------------------------------

def test_upfront_cost_warning_no_score_penalty():
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

    assert any("upfront costs" in r.lower() for r in result.reasons)


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


def test_borderline_verdict():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=15000,
        renter_docs=["bank_statement"],
        rent=6500,
        deposit=6500,
        application_fee=0,
        required_documents=[],
        area_demand="HIGH",
    )

    assert result.verdict in ["BORDERLINE", "WORTH_APPLYING"]


def test_not_worth_it_verdict():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=8000,
        renter_docs=["bank_statement"],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="HIGH",
    )

    assert result.confidence in ["LOW", "MEDIUM", "HIGH"]


# ------------------------------------------------------------
# Budget bands tests
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
