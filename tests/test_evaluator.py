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
        required_documents=["bank_statement"],
        area_demand="LOW",
    )

    assert result.score < 100
    assert any("affordability" in b["title"].lower() for b in result.breakdown)


# ------------------------------------------------------------
# Worker document tests
# ------------------------------------------------------------

def test_bank_statement_penalty_applies_for_workers():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["payslip"],  # missing bank statement
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert any(
        "bank statement" in b["title"].lower() or
        "bank statement" in b["details"].lower()
        for b in result.breakdown
    )


def test_worker_missing_bank_statement_penalty_is_worse_without_payslip():

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
        renter_docs=[],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert without_payslip.score < with_payslip.score

    assert any(
        "payslip" in b["title"].lower() or
        "payslip" in b["details"].lower()
        for b in without_payslip.breakdown
    )


# ------------------------------------------------------------
# Bursary student tests
# ------------------------------------------------------------

def test_bursary_student_no_guarantor_doc_penalties():

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

    assert not any("guarantor" in r.lower() for r in result.reasons)


def test_bursary_shortfall_recommends_guarantor_income():

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

    assert any("does not fully cover" in r.lower() for r in result.reasons)

    assert any("guarantor" in a.lower() for a in result.actions)


# ------------------------------------------------------------
# Non-bursary student tests
# ------------------------------------------------------------

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
        guarantor_monthly_income=0,
        is_bursary_student=False,
    )

    assert result.score < 75


def test_non_bursary_student_affordability_uses_guarantor_income():

    result, bands = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=[
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

    assert bands["recommended"] == 6600


# ------------------------------------------------------------
# Application fee tests
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Confidence tests
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# New professional tests
# ------------------------------------------------------------

def test_new_professional_bank_statement_penalty_is_lighter_with_strong_docs():

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


# ------------------------------------------------------------
# Borderline affordability test (UPDATED FOR CAPE TOWN)
# ------------------------------------------------------------

def test_roommate_suggestion_added_when_borderline_and_rent_above_recommended():

    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=7000,  # 35% -> borderline
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.confidence == "MEDIUM"

    assert any(
        "roommate" in a.lower() or "house" in a.lower()
        for a in result.actions
    )


# ------------------------------------------------------------
# Doc equivalence tests
# ------------------------------------------------------------

def test_student_guarantor_payslip_satisfies_listing_payslip_requirement():

    result, _ = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=[
            "guarantor_letter",
            "guarantor_payslip",
            "guarantor_bank_statement",
        ],
        rent=4500,
        deposit=4500,
        application_fee=0,
        required_documents=["payslip"],
        area_demand="LOW",
        guarantor_monthly_income=20000,
        is_bursary_student=False,
    )

    assert not any(
        "missing required documents" in b["title"].lower()
        for b in result.breakdown
    )


def test_student_guarantor_bank_statement_satisfies_listing_bank_statement_requirement():

    result, _ = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=[
            "guarantor_letter",
            "guarantor_payslip",
            "guarantor_bank_statement",
        ],
        rent=4500,
        deposit=4500,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="LOW",
        guarantor_monthly_income=20000,
        is_bursary_student=False,
    )

    assert not any(
        "missing required documents" in b["title"].lower()
        for b in result.breakdown
    )
