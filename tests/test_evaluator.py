from evaluator import evaluate


def test_affordability_penalty_when_rent_exceeds_upper_limit():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=9000,  # 35% of 20000 = 7000, so this exceeds upper limit
        deposit=9000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="LOW",
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
        area_demand="LOW",
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
        area_demand="LOW",
    )

    assert "Some required documents are missing." in result.reasons


def test_application_fee_high_is_note_for_medium_confidence_not_penalty():
    """
    If confidence is MEDIUM (borderline), application fee should be an informational note,
    not a score penalty.
    """

    # BASELINE: moderate rent, no fee
    result_base, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=6800,  # above recommended band (6000) but under upper limit (7000) -> MEDIUM likely
        deposit=6800,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="MEDIUM",
    )

    # SAME scenario but with high fee
    result_fee, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement", "payslip"],
        rent=6800,
        deposit=6800,
        application_fee=850,
        required_documents=["bank_statement"],
        area_demand="MEDIUM",
    )

    # should include note
    assert any("application fee" in r.lower() for r in result_fee.reasons)

    # score should NOT go down due to fee if confidence is medium
    assert result_fee.confidence == "MEDIUM"
    assert result_fee.score == result_base.score


def test_application_fee_penalty_applies_for_low_confidence():
    """
    If confidence is LOW, high fee should still penalise score.
    """
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=18000,
        renter_docs=["bank_statement"],
        rent=12000,  # very unaffordable -> low confidence likely
        deposit=12000,
        application_fee=850,
        required_documents=["bank_statement"],
        area_demand="HIGH",
    )

    assert result.confidence == "LOW"
    assert any("application fee" in r.lower() for r in result.reasons)
    assert result.score < 60


def test_suggested_budget_bands():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=20000,
        renter_docs=["bank_statement"],
        rent=7000,
        deposit=7000,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="LOW",
    )

    assert bands["conservative"] == 5000
    assert bands["recommended"] == 6000
    assert bands["upper_limit"] == 7000


def test_high_confidence_includes_apply_action():
    result, bands = evaluate(
        renter_type="worker",
        monthly_income=30000,
        renter_docs=["bank_statement", "payslip"],
        rent=7500,  # 25% = 7500, 30% = 9000, so this is strong
        deposit=7500,
        application_fee=0,
        required_documents=["bank_statement"],
        area_demand="LOW",
    )

    assert result.confidence == "HIGH"
    assert any("Apply" in a for a in result.actions)


def test_medium_confidence_suggests_guarantor():
    result, bands = evaluate(
        renter_type="new_professional",
        monthly_income=20000,
        renter_docs=["employment_contract"],  # missing guarantor_letter
        rent=6800,  # slightly above recommended
        deposit=6800,
        application_fee=0,
        required_documents=["employment_contract"],
        area_demand="MEDIUM",
    )

    assert result.confidence == "MEDIUM"
    assert any("guarantor" in a.lower() for a in result.actions)
