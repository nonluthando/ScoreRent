import pytest
from evaluator import evaluate


# ------------------------------------------------------------
# NON-BURSARY STUDENT GUARANTOR TESTS (NEW CORE LOGIC)
# ------------------------------------------------------------

def test_non_bursary_student_with_strong_guarantor_has_no_penalty():

    result, bands = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=[
            "guarantor letter",
            "guarantor payslip",
            "guarantor bank statement"
        ],
        rent=6500,
        deposit=6500,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=32000,
        is_bursary_student=False
    )

    assert result.score >= 75
    assert result.verdict == "WORTH_APPLYING"

    assert any(
        "guarantor fully supports affordability" in b["title"].lower()
        for b in result.breakdown
    )


def test_non_bursary_student_missing_guarantor_income_penalty():

    result, bands = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=[
            "guarantor letter",
            "guarantor payslip",
            "guarantor bank statement"
        ],
        rent=6500,
        deposit=6500,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=0,
        is_bursary_student=False
    )

    assert result.score < 60

    assert any(
        "missing or incomplete guarantor support" in b["title"].lower()
        for b in result.breakdown
    )


def test_non_bursary_student_missing_guarantor_docs_penalty():

    result, bands = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=[
            "guarantor letter"
        ],
        rent=6500,
        deposit=6500,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=30000,
        is_bursary_student=False
    )

    assert result.score < 65

    assert any(
        "missing or incomplete guarantor support" in b["title"].lower()
        for b in result.breakdown
    )


def test_guarantor_income_used_for_affordability():

    result, bands = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=[
            "guarantor letter",
            "guarantor payslip",
            "guarantor bank statement"
        ],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
        guarantor_monthly_income=20000,
        is_bursary_student=False
    )

    # Recommended band should use guarantor income
    assert bands["recommended"] == int(20000 * 0.33)

    assert result.score >= 70


# ------------------------------------------------------------
# BURSARY TESTS
# ------------------------------------------------------------

def test_bursary_student_full_cover_strong_score():

    result, bands = evaluate(
        renter_type="student",
        monthly_income=9000,
        renter_docs=["bursary award letter"],
        rent=6500,
        deposit=6500,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=0,
        is_bursary_student=True
    )

    assert result.score >= 75
    assert result.verdict == "WORTH_APPLYING"


def test_bursary_shortfall_requires_guarantor():

    result, bands = evaluate(
        renter_type="student",
        monthly_income=5000,
        renter_docs=["bursary award letter"],
        rent=7500,
        deposit=7500,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=0,
        is_bursary_student=True
    )

    assert result.score < 60

    assert any(
        "add a guarantor" in a.lower()
        for a in result.actions
    )


# ------------------------------------------------------------
# WORKER TESTS
# ------------------------------------------------------------

def test_worker_good_affordability():

    result, bands = evaluate(
        renter_type="worker",
        monthly_income=28000,
        renter_docs=["payslip", "bank statement"],
        rent=8500,
        deposit=8500,
        application_fee=0,
        required_documents=[],
        area_demand="LOW"
    )

    assert result.score >= 75
    assert result.verdict == "WORTH_APPLYING"


def test_worker_extreme_affordability_penalty():

    result, bands = evaluate(
        renter_type="worker",
        monthly_income=18000,
        renter_docs=["payslip", "bank statement"],
        rent=10000,
        deposit=10000,
        application_fee=0,
        required_documents=[],
        area_demand="HIGH"
    )

    assert result.score < 60
    assert result.verdict == "NOT_WORTH_IT"


# ------------------------------------------------------------
# DEMAND TESTS
# ------------------------------------------------------------

def test_high_demand_penalty_applies():

    result, _ = evaluate(
        renter_type="worker",
        monthly_income=30000,
        renter_docs=["payslip", "bank statement"],
        rent=9000,
        deposit=9000,
        application_fee=0,
        required_documents=[],
        area_demand="HIGH"
    )

    assert any(
        "high demand penalty" in b["title"].lower()
        for b in result.breakdown
    )


def test_low_demand_bonus_applies():

    result, _ = evaluate(
        renter_type="worker",
        monthly_income=30000,
        renter_docs=["payslip", "bank statement"],
        rent=9000,
        deposit=9000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW"
    )

    assert any(
        "low demand bonus" in b["title"].lower()
        for b in result.breakdown
    )
