from target_app.calculator import process_data

def test_basic_division():
    assert process_data(10, 2) == 5.0

def test_rounding_precision():
    # Requires rounding float results to 2 decimal places
    assert process_data(10, 3) == 3.33

def test_zero_division():
    # Requires catching ZeroDivisionError and returning 0.0
    assert process_data(10, 0) == 0.0

def test_string_inputs():
    # Requires casting string representations of numbers to float
    assert process_data("10", "2") == 5.0