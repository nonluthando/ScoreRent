import pytest

from evaluator import evaluate_rental_application


# ============================================================
# Shared Fixtures
# ============================================================

@pytest.fixture
def base_worker_payload():
    """
    Standard worker payload used across multiple tests.
    """

    return {
        "renter_type": "worker",
        "monthly_income": 30000,
        "submitted_documents": [
            "bank statement",
            "payslip",
        ],
        "monthly_rent": 8000,
        "security_deposit": 8000,
        "application_fee": 0,
        "required_documents": [],
        "area_demand": "MEDIUM",
    }


# ============================================================
# Assertion Helpers
# ============================================================

def assert_score_range(result, minimum, maximum):
    """
    Assert result score falls within expected range.
    """

    assert minimum <= result.score <= maximum, (
        f"Score {result.score} "
        f"not in range [{minimum}, {maximum}]"
    )


def assert_reason_contains(result, text):
    """
    Assert at least one reason contains expected text.
    """

    assert any(
        text.lower() in reason.lower()
        for reason in result.reasons
    ), (
        f"Expected reason containing '{text}', "
        f"got {result.reasons}"
    )


def assert_action_contains(result, text):
    """
    Assert at least one action contains expected text.
    """

    assert any(
        text.lower() in action.lower()
        for action in result.actions
    ), (
        f"Expected action containing '{text}', "
        f"got {result.actions}"
    )


# ============================================================
# Worker Affordability Tests
# ============================================================

def test_worker_safe_affordability(
    base_worker_payload,
):
    """
    Worker with healthy affordability ratio
    should receive strong match verdict.
    """

    result, recommended_budget_bands = (
        evaluate_rental_application(
            **base_worker_payload
        )
    )

    assert result.verdict == "STRONG_MATCH"

    assert result.confidence == "HIGH"

    assert_reason_contains(
        result,
        "recommended cape town affordability",
    )

    assert isinstance(
        recommended_budget_bands,
        dict,
    )


def test_worker_extreme_affordability_penalty():
    """
    Extremely high rent-to-income ratio
    should trigger high-risk outcome.
    """

    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=15000,
        submitted_documents=[
            "bank statement",
            "payslip",
        ],
        monthly_rent=9000,
        security_deposit=9000,
        application_fee=500,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.verdict == "HIGH_RISK"

    assert_reason_contains(
        result,
        "significantly above",
    )


# ============================================================
# Demand-Level Tests
# ============================================================

def test_high_demand_penalty_applies():
    """
    High-demand areas should apply score penalty.
    """

    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="HIGH",
    )

    high_demand_entry = next(
        item
        for item in result.breakdown
        if item["title"] == "High-demand rental area"
    )

    assert high_demand_entry["delta"] == -10


def test_low_demand_bonus_applies():
    """
    Lower-demand areas should apply score bonus.
    """

    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    low_demand_entry = next(
        item
        for item in result.breakdown
        if item["title"]
        == "Lower competition rental area"
    )

    assert low_demand_entry["delta"] == 5


# ============================================================
# Required Documents Tests
# ============================================================

def test_missing_required_documents_penalty():
    """
    Missing required documents should apply penalty.
    """

    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[
            "payslip",
        ],
        area_demand="MEDIUM",
    )

    missing_docs_entry = next(
        item
        for item in result.breakdown
        if item["title"]
        == "Missing required documents"
    )

    assert missing_docs_entry["delta"] == -20


# ============================================================
# Bursary Student Tests
# ============================================================

def test_bursary_full_coverage_bonus():
    """
    Fully funded bursary students should
    receive stronger approval outcome.
    """

    result, _ = evaluate_rental_application(
        renter_type="student",
        monthly_income=9000,
        submitted_documents=[
            "nsfas award letter",
        ],
        monthly_rent=7000,
        security_deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        is_bursary_student=True,
    )

    assert result.verdict in [
        "STRONG_MATCH",
        "BORDERLINE",
    ]


def test_bursary_shortfall_requires_guarantor():
    """
    Bursary shortfalls should recommend
    guarantor support.
    """

    result, _ = evaluate_rental_application(
        renter_type="student",
        monthly_income=5000,
        submitted_documents=[
            "nsfas award letter",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        is_bursary_student=True,
    )

    assert_action_contains(
        result,
        "guarantor",
    )


def test_missing_bursary_letter_penalty():
    """
    Missing bursary proof should apply penalty.
    """

    result, _ = evaluate_rental_application(
        renter_type="student",
        monthly_income=8000,
        submitted_documents=[],
        monthly_rent=7000,
        security_deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        is_bursary_student=True,
    )

    assert_reason_contains(
        result,
        "bursary",
    )


# ============================================================
# Non-Bursary Student Guarantor Tests
# ============================================================

def test_non_bursary_student_with_strong_guarantor():
    """
    Strong guarantor support should
    significantly improve approval odds.
    """

    result, _ = evaluate_rental_application(
        renter_type="student",
        monthly_income=0,
        submitted_documents=[
            "guarantor letter",
            "guarantor payslip",
            "guarantor bank statement",
        ],
        monthly_rent=6000,
        security_deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=30000,
        is_bursary_student=False,
    )

    assert_reason_contains(
        result,
        "qualified guarantor",
    )

    assert result.score >= 75


def test_non_bursary_student_missing_guarantor():
    """
    Missing guarantor support should
    strongly reduce approval likelihood.
    """

    result, _ = evaluate_rental_application(
        renter_type="student",
        monthly_income=0,
        submitted_documents=[],
        monthly_rent=6000,
        security_deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=0,
        is_bursary_student=False,
    )

    assert_reason_contains(
        result,
        "guarantor support",
    )

    assert result.score <= 60


def test_guarantor_income_used_for_budget_bands():
    """
    Budget guidance should use guarantor
    income when applicable.
    """

    result, recommended_budget_bands = (
        evaluate_rental_application(
            renter_type="student",
            monthly_income=0,
            submitted_documents=[
                "guarantor letter",
                "guarantor payslip",
                "guarantor bank statement",
            ],
            monthly_rent=7000,
            security_deposit=7000,
            application_fee=0,
            required_documents=[],
            area_demand="MEDIUM",
            guarantor_monthly_income=30000,
            is_bursary_student=False,
        )
    )

    assert (
        recommended_budget_bands["recommended"]
        == int(30000 * 0.33)
    )


# ============================================================
# Confidence Threshold Tests
# ============================================================

def test_high_score_returns_high_confidence():
    """
    Strong scores should map to HIGH confidence.
    """

    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=40000,
        submitted_documents=[
            "bank statement",
            "payslip",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.confidence == "HIGH"


def test_low_score_returns_low_confidence():
    """
    Weak scores should map to LOW confidence.
    """

    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=10000,
        submitted_documents=[
            "bank statement",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[
            "payslip",
        ],
        area_demand="HIGH",
    )

    assert result.confidence == "LOW"


# ============================================================
# Affordability Behaviour Tests
# ============================================================

def test_affordability_penalty_is_monotonic():
    """
    Higher rent burden should always
    reduce score relative to lower burden.
    """

    lower_rent_result, _ = (
        evaluate_rental_application(
            renter_type="worker",
            monthly_income=20000,
            submitted_documents=[
                "bank statement",
                "payslip",
            ],
            monthly_rent=7000,
            security_deposit=0,
            application_fee=0,
            required_documents=[],
            area_demand="MEDIUM",
        )
    )

    higher_rent_result, _ = (
        evaluate_rental_application(
            renter_type="worker",
            monthly_income=20000,
            submitted_documents=[
                "bank statement",
                "payslip",
            ],
            monthly_rent=8000,
            security_deposit=0,
            application_fee=0,
            required_documents=[],
            area_demand="MEDIUM",
        )
    )

    assert (
        higher_rent_result.score
        < lower_rent_result.score
    )


# ============================================================
# Invalid / Edge Case Tests
# ============================================================

def test_zero_income_does_not_crash():
    """
    Zero-income scenarios should safely
    return high-risk outcome.
    """

    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=0,
        submitted_documents=[
            "bank statement",
        ],
        monthly_rent=6000,
        security_deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.score >= 0

    assert result.verdict == "HIGH_RISK"


def test_invalid_renter_type_defaults_to_worker():
    """
    Invalid renter types should safely
    fallback to worker classification.
    """

    result, _ = evaluate_rental_application(
        renter_type="alien",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
        ],
        monthly_rent=8000,
        security_deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.score > 0


def test_invalid_demand_level_defaults_to_medium():
    """
    Invalid demand levels should safely
    fallback to MEDIUM.
    """

    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
        ],
        monthly_rent=8000,
        security_deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="EXTREME",
    )

    assert result.score > 0


# ============================================================
# Upfront Burden Tests
# ============================================================

def test_upfront_burden_adds_warning_not_penalty():
    """
    Upfront cost warnings should not
    directly reduce score.
    """

    normal_result, _ = (
        evaluate_rental_application(
            renter_type="worker",
            monthly_income=30000,
            submitted_documents=[
                "bank statement",
                "payslip",
            ],
            monthly_rent=8000,
            security_deposit=8000,
            application_fee=0,
            required_documents=[],
            area_demand="MEDIUM",
        )
    )

    heavy_upfront_result, _ = (
        evaluate_rental_application(
            renter_type="worker",
            monthly_income=30000,
            submitted_documents=[
                "bank statement",
                "payslip",
            ],
            monthly_rent=8000,
            security_deposit=90000,
            application_fee=0,
            required_documents=[],
            area_demand="MEDIUM",
        )
    )

    assert (
        heavy_upfront_result.score
        == normal_result.score
    )

    assert any(
        "upfront" in reason.lower()
        for reason in heavy_upfront_result.reasons
    )


# ============================================================
# Score Clamping Tests
# ============================================================

def test_score_never_negative():
    """
    Score should never fall below zero.
    """

    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=10000,
        submitted_documents=[],
        monthly_rent=20000,
        security_deposit=0,
        application_fee=0,
        required_documents=[
            "payslip",
        ],
        area_demand="HIGH",
    )

    assert result.score >= 0


def test_score_never_exceeds_100():
    """
    Score should never exceed maximum cap.
    """

    result, _ = evaluate_rental_application(
        renter_type="student",
        monthly_income=20000,
        submitted_documents=[
            "guarantor letter",
            "guarantor payslip",
            "guarantor bank statement",
        ],
        monthly_rent=2000,
        security_deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
        guarantor_monthly_income=50000,
        is_bursary_student=False,
    )

    assert result.score <= 100


# ============================================================
# Breakdown Integrity Tests
# ============================================================

def test_breakdown_entries_are_mathematically_consistent():
    """
    Every score adjustment entry should satisfy:

        after = before + delta
    """

    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=10000,
        submitted_documents=[
            "bank statement",
        ],
        monthly_rent=8000,
        security_deposit=0,
        application_fee=0,
        required_documents=[
            "payslip",
        ],
        area_demand="HIGH",
    )

    for entry in result.breakdown:

        assert (
            entry["after"]
            == entry["before"] + entry["delta"]
        )


def test_breakdown_has_expected_order():
    """
    Breakdown should begin with base score
    and end with final verdict.
    """

    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
        ],
        monthly_rent=8000,
        security_deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert (
        result.breakdown[0]["title"]
        == "Base match score"
    )

    assert (
        result.breakdown[-1]["title"]
        == "Final verdict"
    )
