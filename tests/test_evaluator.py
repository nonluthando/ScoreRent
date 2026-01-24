from evaluator import evaluate


def test_affordability_penalty_when_rent_exceeds_upper_limit():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=9000,  # exceeds 35% band (7000)
        deposit=9000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="LOW"
    )

    assert result.score < 70
    assert "Rent exceeds the recommended affordability limit (35% of income)." in result.reasons


def test_missing_bank_statement_penalty_applies_universally():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["payslip"],  # missing bank_statement
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="LOW"
    )

    assert any("No bank statement provided" in r for r in result.reasons)


def test_missing_required_documents_penalty():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement"],  # missing payslip
        rent=6500,
        deposit=6500,
        application_fee=0,
        required_documents=["bank_statement", "payslip"],
        area_demand="LOW"
    )

    assert "Some required documents are missing." in result.reasons


def test_application_fee_risk_penalty():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=18000,
        renter_docs=["bank_statement"],
        rent=7500,
        deposit=7500,
        application_fee=850,
        required_documents=["bank_statement"],
        area_demand="HIGH"
    )

    assert "High application fee increases cost of a low-confidence application." in result.reasons
    assert result.score < 70


def test_suggested_budget_bands():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement"],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="LOW"
    )

    assert bands["conservative"] == 5000
    assert bands["recommended"] == 6000
    assert bands["upper_limit"] == 7000
