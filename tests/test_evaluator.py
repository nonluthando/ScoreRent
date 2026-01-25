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

    assert any("bank statement" in r.lower() for r in result.reasons)


def test_worker_missing_bank_statement_penalty_is_worse_without_payslip():
    """
    Worker missing bank statement should be penalised more if payslip is also missing.
    """
    with_payslip, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["payslip"],  # missing bank statement
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    without_payslip, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=[],  # missing bank statement + payslip
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert without_payslip.score < with_payslip.score
    assert any("payslip" in r.lower() for r in without_payslip.reasons)


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

    assert not any("bank statement" in r.lower() for r in result.reasons)
    assert not any("guarantor bank statement" in r.lower() for r in result.reasons)


def test_bursary_shortfall_recommends_guarantor_income():
    result, bands = evaluate(
        renter_type="student",
        monthly_income=5000,
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
        renter_docs=[
            "proof_of_registration",
            "guarantor_letter",
            "guarantor_payslip",
            "guarantor_bank_statement",
        ],
        rent=5000,
        deposit=5000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=0,  # missing
    )

    assert any("guarantor income" in r.lower() for r in result.reasons)


def test_non_bursary_student_affordability_uses_guarantor_income():
    result, bands = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=[
            "proof_of_registration",
            "guarantor_letter",
            "guarantor_payslip",
            "guarantor_bank_statement",
        ],
        rent=5800,
        deposit=5800,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
        guarantor_monthly_income=20000,
    )

    assert result.score > 50
    assert bands["recommended"] == 6000


def test_application_fee_is_informational_only_not_penalty():
    """
    Application fee should add a reason but NOT reduce score.
    """
    no_fee, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=6800,
        deposit=6800,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    high_fee, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=6800,
        deposit=6800,
        application_fee=800,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert high_fee.score == no_fee.score
    assert "application fee" in " ".join(high_fee.reasons).lower()


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


def test_cluster_penalty_only_applies_to_student_or_new_professional():
    """
    Cluster penalty should NOT apply to worker.
    Workers are handled explicitly via bank_statement/payslip rules.
    """
    worker_res, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement"],  # missing payslip
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert any("payslip" in r.lower() for r in worker_res.reasons)
    assert not any("recommended documents" in r.lower() for r in worker_res.reasons)

    np_res, _ = evaluate(
        renter_type="new_professional",
        monthly_income=20000,
        renter_docs=["employment_contract"],  # missing guarantor_letter
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert any("recommended documents" in r.lower() for r in np_res.reasons)


def test_upfront_cost_is_informational_only_no_score_penalty():
    """
    Upfront cost warning should NOT reduce score anymore.
    """
    res_high_upfront, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=6000,
        deposit=20000,
        application_fee=1000,
        required_documents=[],
        area_demand="LOW",
    )

    res_low_upfront, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=6000,
        deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert res_high_upfront.score == res_low_upfront.score
    assert any("upfront cost" in r.lower() for r in res_high_upfront.reasons)


def test_new_professional_bank_statement_penalty_is_lighter_with_strong_docs():
    """
    New professional: missing bank statement is penalised less if they have:
    employment_contract + guarantor_letter.
    """
    strong_docs, _ = evaluate(
        renter_type="new_professional",
        monthly_income=20000,
        renter_docs=["employment_contract", "guarantor_letter"],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    weak_docs, _ = evaluate(
        renter_type="new_professional",
        monthly_income=20000,
        renter_docs=[],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert strong_docs.score > weak_docs.score
    assert any("bank statement" in r.lower() for r in strong_docs.reasons)


def test_roommate_suggestion_added_when_borderline_and_rent_above_recommended():
    """
    When confidence is MEDIUM and rent > recommended,
    evaluator should suggest house-sharing.
    """
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=6500,  # recommended = 6000
        deposit=6500,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.confidence == "MEDIUM"
    assert any("roommates" in a.lower() or "house" in a.lower() for a in result.actions)
