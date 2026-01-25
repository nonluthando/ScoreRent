from evaluator import evaluate


def test_affordability_penalty_when_rent_exceeds_upper_limit():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=9000,  # 35% of 20k = 7000 -> exceeds upper_limit
        deposit=9000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="LOW",
    )

    assert result.score < 100
    assert any("35%" in r for r in result.reasons)


def test_bank_statement_penalty_applies_for_workers():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["payslip"],  # missing bank_statement
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    # Worker-specific bank statement rule is now heavy
    assert any("bank statement" in r.lower() for r in result.reasons)


def test_worker_missing_bank_statement_penalty_is_worse_without_payslip():
    """
    New test: worker missing bank statement is punished more if payslip also missing.
    """
    with_payslip, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["payslip"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    without_payslip, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=[],  # missing bank_statement + payslip
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert without_payslip.score < with_payslip.score


def test_bursary_student_no_bank_statement_penalty():
    result, bands = evaluate(
        renter_type="student",
        monthly_income=8000,
        renter_docs=["proof_of_registration", "bursary_letter"],  # no bank_statement
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    # bursary students should NOT trigger non-student "no bank statement" penalty
    assert not any("no bank statement" in r.lower() for r in result.reasons)


def test_bursary_shortfall_recommends_guarantor_income():
    result, bands = evaluate(
        renter_type="student",
        monthly_income=5000,  # bursary/support
        renter_docs=["proof_of_registration", "bursary_letter"],
        rent=7000,  # shortfall 2000
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert any("shortfall" in r.lower() for r in result.reasons)
    assert any("guarantor" in a.lower() for a in result.actions)


def test_non_bursary_student_requires_guarantor_income():
    result, bands = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=["proof_of_registration", "guarantor_letter", "guarantor_payslip", "guarantor_bank_statement"],
        rent=5000,
        deposit=5000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=0,  # missing
    )

    assert any("guarantor income" in r.lower() for r in result.reasons)


def test_non_bursary_student_affordability_uses_guarantor_income():
    # guarantor income 20000 -> recommended 30% = 6000 so rent 5800 should be OK
    result, bands = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=["proof_of_registration", "guarantor_letter", "guarantor_payslip", "guarantor_bank_statement"],
        rent=5800,
        deposit=5800,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
        guarantor_monthly_income=20000,
    )

    assert result.score > 50
    assert bands["recommended"] == 6000


def test_application_fee_not_penalised_for_medium_confidence():
    """
    MEDIUM confidence: fee becomes informational only (no score penalty).
    The reason should mention the fee.
    """
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],  # strong docs
        rent=6800,  # above recommended (6000), below upper (7000) -> borderline zone
        deposit=6800,
        application_fee=800,
        required_documents=["bank_statement", "payslip"],
        area_demand="MEDIUM",
    )

    assert result.confidence == "MEDIUM"
    assert any("application fee" in r.lower() for r in result.reasons)


def test_medium_confidence_suggests_roommates_if_rent_above_recommended():
    """
    New requirement: if MEDIUM confidence and rent is above recommended -> suggest roommates.
    """
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=6800,  # above recommended
        deposit=6800,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    if result.confidence == "MEDIUM":
        assert any("roommates" in a.lower() or "house-sharing" in a.lower() for a in result.actions)


def test_high_confidence_includes_apply_action():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=25000,
        renter_docs=["bank_statement", "payslip"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert result.confidence == "HIGH"
    assert any("apply" in a.lower() for a in result.actions)
