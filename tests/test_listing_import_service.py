from services.listing_import_service import (
    GeminiListingExtraction,
    GeminiMoneyField,
    GeminiTextField,
    _to_listing_extraction,
)


def make_result(**overrides):
    values = {
        "listing_name": GeminiTextField(value="Observatory studio", evidence="Observatory studio", confidence="high"),
        "location": GeminiTextField(value="Observatory, Cape Town", evidence="Observatory", confidence="high"),
        "rent": GeminiMoneyField(value=8500, evidence="Rent R8 500 pm", confidence="high"),
        "deposit": GeminiMoneyField(value=8500, evidence="Deposit R8 500", confidence="high"),
        "application_fee": GeminiMoneyField(value=250, evidence="Application fee R250", confidence="high"),
        "required_documents": ["proof of income", "three months bank statements"],
        "warnings": [],
        "visible_text_summary": "Rent R8 500 pm. Deposit R8 500.",
    }
    values.update(overrides)
    return GeminiListingExtraction(**values)


def test_maps_structured_gemini_response_to_existing_listing_schema():
    result = _to_listing_extraction(make_result())

    assert result.rent.value == 8500
    assert result.deposit.value == 8500
    assert result.application_fee.value == 250
    assert result.location.value == "Observatory, Cape Town"
    assert result.required_documents == ["payslip", "bank statement"]


def test_missing_deposit_remains_none_instead_of_zero():
    result = _to_listing_extraction(
        make_result(deposit=GeminiMoneyField(value=None, evidence=None, confidence="low"))
    )

    assert result.deposit.value is None
    assert any("Do not assume it is R0" in warning for warning in result.warnings)


def test_repeated_documents_and_warnings_are_deduplicated():
    result = _to_listing_extraction(
        make_result(
            required_documents=["payslip", "payslip"],
            warnings=["Check the deposit.", "Check the deposit."],
        )
    )

    assert result.required_documents == ["payslip"]
    assert result.warnings.count("Check the deposit.") == 1
