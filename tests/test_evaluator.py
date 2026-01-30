from evaluator import evaluate


def test_affordability_penalty_when_rent_exceeds_upper_limit():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=9000,  # 45% of 20k, should trigger >40% penalty
        deposit=9000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="LOW",
    )

    assert result.score < 60
    assert any("over 40%" in r.lower() for r in result.reasons)


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


def test_bursary_student_skips_affordability_penalties_when_support_covers_rent():
    result, bands = evaluate(
        renter_type="student",
        monthly_income=8000,
        renter_docs=[],  # bursary is controlled by flag now
        rent=8000,
        deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        is_bursary_student=True,
    )

    assert result.score >= 90
    assert any("covers rent" in r.lower() for r in result.reasons)


def test_bursary_shortfall_recommends_guarantor_income():
    result, bands = evaluate(
        renter_type="student",
        monthly_income=5000,
        renter_docs=[],
        rent=7000,  # shortfall 2000
        deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        is_bursary_student=True,
    )

    assert any("shortfall" in r.lower() for r in result.reasons)
    assert any("guarantor" in a.lower() for a in result.actions)


def test_non_bursary_student_requires_guarantor_income():
    result, bands = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=[
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
        is_bursary_student=False,
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
        is_bursary_student=False,
    )

    assert result.score > 50
    assert bands["recommended"] == 6000


def test_application_fee_is_informational_only_not_penalty():
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


def test_missing_required_docs_penalty_scales_by_count():
    res_one, _ = evaluate(
        renter_type="worker",
        monthly_income=25000,
        renter_docs=["bank_statement", "payslip"],
        rent=6000,
        deposit=0,
        application_fee=0,
        required_documents=["bank_statement"],  # already has it
        area_demand="MEDIUM",
    )

    res_two, _ = evaluate(
        renter_type="worker",
        monthly_income=25000,
        renter_docs=["bank_statement", "payslip"],
        rent=6000,
        deposit=0,
        application_fee=0,
        required_documents=["bank_statement", "payslip", "proof_of_income_letter"],  # missing one
        area_demand="MEDIUM",
    )

    assert res_two.score < res_one.score
    assert any("missing required listing documents" in b["title"].lower() for b in res_two.breakdown)


def test_new_professional_missing_bank_and_payslip_is_not_as_harsh_as_worker():
    worker_res, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=[],
        rent=6000,
        deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    np_res, _ = evaluate(
        renter_type="new_professional",
        monthly_income=20000,
        renter_docs=[],
        rent=6000,
        deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert np_res.score > worker_res.score


def test_new_professional_employment_contract_boosts_score():
    weak_docs, _ = evaluate(
        renter_type="new_professional",
        monthly_income=20000,
        renter_docs=[],
        rent=6000,
        deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    strong_docs, _ = evaluate(
        renter_type="new_professional",
        monthly_income=20000,
        renter_docs=["employment_contract"],
        rent=6000,
        deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert strong_docs.score > weak_docs.score
    assert any("employment contract" in r.lower() for r in strong_docs.reasons)


def test_student_missing_proof_of_registration_is_soft_penalty_not_hard_fail():
    """
    Student might not have proof of registration yet (e.g. before February),
    so we only apply a small penalty.
    """
    res, _ = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=[
            "guarantor_letter",
            "guarantor_payslip",
            "guarantor_bank_statement",
        ],
        rent=5000,
        deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
        guarantor_monthly_income=25000,
        is_bursary_student=False,
    )

    assert res.score >= 60
    assert any("proof of registration" in r.lower() for r in res.reasons)


def test_contact_agent_suggestion_appears_when_medium_or_low_confidence():
    res, _ = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement"],  # missing payslip
        rent=8000,  # 40%
        deposit=0,
        application_fee=800,
        required_documents=[],
        area_demand="HIGH",
    )

    assert res.confidence in ("MEDIUM", "LOW")
    assert any("contact the agent" in a.lower() for a in res.actions)
