from evaluator import evaluate


def make_obj(**kwargs):
    return type("Obj", (), kwargs)


def test_affordability_penalty_when_rent_exceeds_budget():
    renter = make_obj(
        monthly_income=20000,
        budget=7000,
        documents=["bank_statement", "payslip"]
    )
    listing = make_obj(
        rent=9000,  # exceeds budget
        deposit=9000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="LOW"
    )

    score, verdict, reasons, suggested = evaluate(renter, listing)

    assert score < 100
    assert "Rent exceeds stated budget" in reasons


def test_missing_bank_statement_penalty_applies_universally():
    renter = make_obj(
        monthly_income=20000,
        budget=8000,
        documents=["payslip"]  # no bank_statement
    )
    listing = make_obj(
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="LOW"
    )

    score, verdict, reasons, suggested = evaluate(renter, listing)

    assert any("No bank statement" in r for r in reasons)


def test_cluster_proof_reduces_document_mismatch_penalty():
    renter = make_obj(
        monthly_income=20000,
        budget=8000,
        documents=["employment_contract", "guarantor_letter"]
    )
    listing = make_obj(
        rent=7500,
        deposit=7500,
        application_fee=0,
        required_documents=["bank_statement"],  # strict requirement missing
        area_demand="LOW"
    )

    score, verdict, reasons, suggested = evaluate(renter, listing)

    assert "Some required documents are missing, but alternative proof is available" in reasons


def test_application_fee_risk_penalty():
    renter = make_obj(
        monthly_income=18000,
        budget=7000,
        documents=["bank_statement"]
    )
    listing = make_obj(
        rent=7500,
        deposit=7500,
        application_fee=850,
        required_documents=["bank_statement"],
        area_demand="HIGH"
    )

    score, verdict, reasons, suggested = evaluate(renter, listing)

    assert "High application fee relative to budget" in reasons
    assert score < 100


def test_suggested_budget_bands():
    renter = make_obj(
        monthly_income=20000,
        budget=7000,
        documents=["bank_statement"]
    )
    listing = make_obj(
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="LOW"
    )

    score, verdict, reasons, suggested = evaluate(renter, listing)

    assert suggested["conservative"] == 5000
    assert suggested["recommended"] == 6000
    assert suggested["upper_limit"] == 7000
