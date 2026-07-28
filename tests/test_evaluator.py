from evaluator import evaluate_rental_application
from conftest import (
    assert_action_contains,
    assert_reason_contains,
)


# ============================================================
# Worker Affordability Tests
# ============================================================

def test_worker_safe_affordability(worker_payload):
    worker_payload["required_documents"] = [
        "bank statement",
        "payslip",
    ]

    result, budget = evaluate_rental_application(**worker_payload)

    assert result.verdict == "STRONG_MATCH"
    assert result.confidence == "HIGH"

    assert_reason_contains(
        result,
        "healthy affordability range",
    )

    assert isinstance(budget, dict)


def test_worker_extreme_affordability_penalty():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=15000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
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
        "very high compared",
    )


def test_affordability_penalty_is_monotonic():
    lower_result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=20000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=7000,
        security_deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    higher_result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=20000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert higher_result.score < lower_result.score


# ============================================================
# Demand Level Tests
# ============================================================

def test_high_demand_penalty_applies():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="HIGH",
    )

    entry = next(
        item
        for item in result.breakdown
        if item["title"] == "High-demand rental area"
    )

    assert entry["delta"] == -10

    assert_reason_contains(
        result,
        "high-demand area",
    )

    assert_action_contains(
        result,
        "complete document pack",
    )


def test_low_demand_bonus_applies():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="LOW",
    )

    entry = next(
        item
        for item in result.breakdown
        if item["title"] == "Lower competition rental area"
    )

    assert entry["delta"] == 5

    assert_reason_contains(
        result,
        "lower area demand",
    )


# ============================================================
# Required Documents
# ============================================================

def test_missing_required_documents_penalty():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[
            "payslip",
        ],
        area_demand="MEDIUM",
    )

    entry = next(
        item
        for item in result.breakdown
        if item["title"] == "Missing required documents"
    )

    assert entry["delta"] == -20

    assert_reason_contains(
        result,
        "not currently covered",
    )

    assert_action_contains(
        result,
        "payslip",
    )


def test_document_alias_matching_detects_bank_statement_and_payslip():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "3 months bank statements",
            "latest payslip",
            "letter of employment",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[
            "bank statement",
            "payslip",
        ],
        area_demand="MEDIUM",
    )

    missing_required_entries = [
        item
        for item in result.breakdown
        if item["title"] == "Missing required documents"
    ]

    assert missing_required_entries == []


def test_new_professional_accepts_contract_or_offer_letter():
    result, _ = evaluate_rental_application(
        renter_type="new_professional",
        monthly_income=30000,
        submitted_documents=[
            "offer letter",
            "bank statement",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    missing_profile_entries = [
        item
        for item in result.breakdown
        if item["title"] == "Missing renter profile documents"
    ]

    assert missing_profile_entries == []


# ============================================================
# Bursary Student Tests
# ============================================================

def test_bursary_full_coverage_bonus(student_payload):
    result, _ = evaluate_rental_application(**student_payload)

    assert result.verdict in (
        "STRONG_MATCH",
        "BORDERLINE",
    )

    assert_reason_contains(
        result,
        "funding appears to cover",
    )


def test_bursary_shortfall_requires_guarantor():
    result, _ = evaluate_rental_application(
        renter_type="student",
        monthly_income=5000,
        submitted_documents=[
            "nsfas award letter",
            "proof of registration",
            "student id",
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


def test_missing_bursary_letter_penalty_and_affordability_runs():
    result, _ = evaluate_rental_application(
        renter_type="student",
        monthly_income=0,
        submitted_documents=[
            "proof of registration",
            "student id",
        ],
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

    assert_reason_contains(
        result,
        "affordability cannot be verified",
    )


# ============================================================
# Non-Bursary Student Guarantor Tests
# ============================================================

def test_non_bursary_student_with_strong_guarantor():
    result, _ = evaluate_rental_application(
        renter_type="student",
        monthly_income=0,
        submitted_documents=[
            "guarantor letter",
            "guarantor payslip",
            "guarantor bank statement",
            "proof of registration",
            "student id",
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
        "guarantor income",
    )

    assert result.score >= 75


def test_non_bursary_student_with_own_income_is_not_auto_penalised():
    result, _ = evaluate_rental_application(
        renter_type="student",
        monthly_income=30000,
        submitted_documents=[
            "proof of registration",
            "student id",
        ],
        monthly_rent=6000,
        security_deposit=6000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=0,
        is_bursary_student=False,
    )

    missing_guarantor_entries = [
        item
        for item in result.breakdown
        if item["title"] == "Missing guarantor support"
    ]

    assert missing_guarantor_entries == []

    assert_reason_contains(
        result,
        "own declared monthly income or support",
    )


def test_non_bursary_student_missing_guarantor():
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
        "complete guarantor file",
    )

    assert result.score <= 60


def test_guarantor_income_used_for_budget_bands():
    _, budget = evaluate_rental_application(
        renter_type="student",
        monthly_income=0,
        submitted_documents=[
            "guarantor letter",
            "guarantor payslip",
            "guarantor bank statement",
            "proof of registration",
            "student id",
        ],
        monthly_rent=7000,
        security_deposit=7000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
        guarantor_monthly_income=30000,
        is_bursary_student=False,
    )

    assert budget["recommended"] == int(30000 * 0.33)


# ============================================================
# Confidence Tests
# ============================================================

def test_complete_inputs_return_high_confidence():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=40000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[
            "bank statement",
            "payslip",
        ],
        area_demand="MEDIUM",
    )

    assert result.confidence == "HIGH"


def test_missing_listing_requirements_reduce_confidence():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=40000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.verdict == "STRONG_MATCH"
    assert result.confidence == "MEDIUM"

    assert_reason_contains(
        result,
        "No listing-specific document requirements were entered",
    )


def test_incomplete_inputs_return_low_confidence():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=0,
        submitted_documents=[],
        monthly_rent=0,
        security_deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.confidence == "LOW"


# ============================================================
# Invalid Input Tests
# ============================================================

def test_zero_income_does_not_crash():
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

    assert_reason_contains(
        result,
        "affordability cannot be verified",
    )

    assert_action_contains(
        result,
        "income",
    )


def test_invalid_renter_type_defaults_to_worker():
    result, _ = evaluate_rental_application(
        renter_type="alien",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.score > 0


def test_invalid_demand_level_defaults_to_medium():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="EXTREME",
    )

    assert result.score > 0

    assert_reason_contains(
        result,
        "area demand is moderate",
    )


# ============================================================
# Upfront Cost Tests
# ============================================================

def test_moderate_upfront_burden_adds_warning_not_penalty():
    normal_result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    moderate_result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=30000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert moderate_result.score == normal_result.score

    assert_reason_contains(
        moderate_result,
        "moderately high",
    )


def test_severe_upfront_burden_adds_penalty():
    normal_result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    heavy_result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=90000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert heavy_result.score < normal_result.score

    entry = next(
        item
        for item in heavy_result.breakdown
        if item["title"] == "Severe upfront cost pressure"
    )

    assert entry["delta"] == -15

    assert_reason_contains(
        heavy_result,
        "upfront cost",
    )

    assert_action_contains(
        heavy_result,
        "savings",
    )


# ============================================================
# Score Clamping Tests
# ============================================================

def test_score_never_negative():
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
    result, _ = evaluate_rental_application(
        renter_type="student",
        monthly_income=20000,
        submitted_documents=[
            "guarantor letter",
            "guarantor payslip",
            "guarantor bank statement",
            "proof of registration",
            "student id",
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
# Recommendation / Action Tests
# ============================================================

def test_strong_match_gets_apply_recommendation():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=40000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.verdict == "STRONG_MATCH"

    assert_action_contains(
        result,
        "worth applying",
    )


def test_borderline_gets_improvement_recommendation():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=20000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=7600,
        security_deposit=7600,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.verdict == "BORDERLINE"

    assert_action_contains(
        result,
        "affordability",
    )


def test_high_risk_gets_skip_recommendation():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=10000,
        submitted_documents=[],
        monthly_rent=8000,
        security_deposit=8000,
        application_fee=0,
        required_documents=[
            "payslip",
        ],
        area_demand="HIGH",
    )

    assert result.verdict == "HIGH_RISK"

    assert_action_contains(
        result,
        "skipping this listing",
    )


# ============================================================
# Breakdown Tests
# ============================================================

def test_breakdown_has_expected_order():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    assert result.breakdown[0]["title"] == "Base match score"
    assert result.breakdown[-1]["title"] == "Final verdict"


def test_breakdown_contains_final_verdict_details():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank statement",
            "payslip",
            "employment letter",
        ],
        monthly_rent=8000,
        security_deposit=0,
        application_fee=0,
        required_documents=[],
        area_demand="MEDIUM",
    )

    final_entry = result.breakdown[-1]

    assert final_entry["title"] == "Final verdict"
    assert result.verdict in final_entry["details"]
    assert result.confidence in final_entry["details"]

def test_snake_case_document_values_are_normalized():
    result, _ = evaluate_rental_application(
        renter_type="worker",
        monthly_income=30000,
        submitted_documents=[
            "bank_statement",
            "payslip",
        ],
        monthly_rent=7000,
        security_deposit=7000,
        application_fee=0,
        required_documents=[
            "bank_statement",
            "payslip",
        ],
        area_demand="MEDIUM",
    )

    missing_profile_entries = [
        item
        for item in result.breakdown
        if item["title"] == "Missing renter profile documents"
    ]

    missing_required_entries = [
        item
        for item in result.breakdown
        if item["title"] == "Missing required documents"
    ]

    assert missing_profile_entries == []
    assert missing_required_entries == []
