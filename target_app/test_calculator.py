import pytest
from target_app.calculator import process_data


def test_formatted_strings():
    assert process_data(" $10.00 ", " 2 ") == 5.0


def test_zero_division_fallback():
    # Expect zero division to return 0.0
    assert process_data("$50", "0") == 0.0


def test_precision_rounding():
    assert process_data("10", "3") == 3.33