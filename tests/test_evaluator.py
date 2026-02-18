import pytest
from evaluator import evaluate, EvaluationResult


# ------------------------------------------------------------
# Helper assertion
# ------------------------------------------------------------

def assert_score_range(result, low, high):
    assert low <= result.score <= high, f"Score {result.score} not in range [{low},{high}]"


def assert_reason_contains(result, text):
    assert any(text.lower() in r.lower() for r in result.reasons), \
        f"Expected reason containing '{text}', got {result.reasons}"


def assert_action_contains(result, text):
    assert any(text.lower() in a.lower() for a in result.actions), \
        f"Expected action containing '{text}', got {result.actions}"


# ------------------------------------------------------------
# Worker tests
# ------------------------------------------------------------

def test_worker_safe_affordability():

    result, bands = evaluate(
        renter_type="worker",
        monthly_income=30000,
        renter_docs=["bank statement", "payslip"],
        rent=8000,
        deposit=8000,
        application_fee=500,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.verdict == "WORTH_APPLYING"
    assert result.confidence == "HIGH"
    assert_reason_contains(result, "within safe approval range")


def test_worker_extreme_affordability_penalty():

    result, _ = evaluate(
        renter_type="worker",
        monthly_income=15000,
        renter_docs=["bank statement", "payslip"],
        rent=9000,
        deposit=9000,
        application_fee=500,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.verdict == "NOT_WORTH_IT"
    assert_reason_contains(result, "far above typical approval range")


# ------------------------------------------------------------
# Demand tests
# ------------------------------------------------------------

def test_high_demand_penalty_applies():

    result, _ = evaluate(
        renter_type="worker",
        monthly_income=30000,
        renter_docs=["bank statement", "payslip"],
        rent=8000,
        deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="HIGH",
    )

    assert any("High demand area" in b["title"] for b in result.breakdown)


def test_low_demand_bonus_applies():

    result, _ = evaluate(
        renter_type="worker",
        monthly_income=30000,
        renter_docs=["bank statement", "payslip"],
        rent=8000,
        deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    assert any("Low demand area" in b["title"] for b in result.breakdown)


# ------------------------------------------------------------
# Required documents tests
# ------------------------------------------------------------

def test_missing_required_documents_penalty():

    result, _ = evaluate(
        renter_type="worker",
        monthly_income=30000,
        renter_docs=["bank statement"],
        rent=8000,
        deposit=8000,
        application_fee=0,
        required_documents=["payslip"],
        area_demand="MEDIUM",
    )

    assert any("Missing required documents" in b["title"] for b in result.breakdown)


# ------------------------------------------------------------
# Bursary student tests
# ------------------------------------------------------------

def test_bursary_full_coverage_bonus():

    result, _ = evaluate(
        renter_type="student",
        monthly_income=9000,
        renter_docs=["nsfas award letter"],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        is_bursary_student=True,
    )

    assert result.verdict in ["WORTH_APPLYING", "BORDERLINE"]


def test_bursary_shortfall_requires_guarantor():

    result, _ = evaluate(
        renter_type="student",
        monthly_income=5000,
        renter_docs=["nsfas award letter"],
        rent=8000,
        deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        is_bursary_student=True,
    )

    assert_action_contains(result, "guarantor income")


def test_missing_bursary_letter_penalty():

    result, _ = evaluate(
        renter_type="student",
        monthly_income=8000,
        renter_docs=[],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        is_bursary_student=True,
    )

    assert_reason_contains(result, "bursary award letter is missing")


# ------------------------------------------------------------
# Non-bursary student guarantor tests
# ------------------------------------------------------------

def test_non_bursary_student_with_strong_guarantor_has_no_penalty():

    result, _ = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=[
            "guarantor letter",
            "guarantor payslip",
            "guarantor bank statement",
        ],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=30000,
        is_bursary_student=False,
    )

    assert_reason_contains(result, "financially qualified guarantor")
    assert result.score >= 75


def test_non_bursary_student_missing_guarantor_penalty():

    result, _ = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=[],
        rent=6000,
        deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=0,
        is_bursary_student=False,
    )

    assert_reason_contains(result, "require full guarantor support")
    assert result.score <= 60


def test_non_bursary_student_guarantor_income_used_for_affordability():

    result, bands = evaluate(
        renter_type="student",
        monthly_income=0,
        renter_docs=[
            "guarantor letter",
            "guarantor payslip",
            "guarantor bank statement",
        ],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=30000,
        is_bursary_student=False,
    )

    assert bands["recommended"] == int(30000 * 0.33)


# ------------------------------------------------------------
# Verdict threshold tests
# ------------------------------------------------------------

def test_high_score_returns_high_confidence():

    result, _ = evaluate(
        renter_type="worker",
        monthly_income=40000,
        renter_docs=["bank statement", "payslip"],
        rent=8000,
        deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.confidence == "HIGH"


def test_low_score_returns_low_confidence():

    result, _ = evaluate(
        renter_type="worker",
        monthly_income=10000,
        renter_docs=["bank statement"],
        rent=8000,
        deposit=8000,
        application_fee=0,
        required_documents=["payslip"],
        area_demand="HIGH",
    )

    assert result.confidence == "LOW"
       
