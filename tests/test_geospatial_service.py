from services.geospatial_service import SUPPORTED_TRAVEL_MODES


def test_supported_modes_are_limited_to_mvp_modes():
    assert SUPPORTED_TRAVEL_MODES == {"drive", "walk", "bicycle"}
