from typing import Union

def add(a: int, b: int) -> int:
    """
    Adds two integers and returns their sum.

    Args:
        a: The first integer.
        b: The second integer.

    Returns:
        The sum of the two integers.
    """
    return a + b

def multiply(a: int, b: int) -> int:
    """
    Multiplies two integers and returns their product.

    Args:
        a: The first integer.
        b: The second integer.

    Returns:
        The product of the two integers.
    """
    return a * b

from target_app.utils import sanitize_input

def process_data(a: Union[int, float, str], b: Union[int, float, str]) -> float:
    """
    Processes two inputs, sanitizing them, converting to floats, and performing division.
    Handles division by zero by returning 0.0 and rounds valid results to 2 decimal places.

    Args:
        a: The first input, which can be an integer, float, or string representation of a number.
        b: The second input, which can be an integer, float, or string representation of a number.

    Returns:
        The result of the division, rounded to 2 decimal places, or 0.0 if division by zero
        occurs or if `sanitize_input` fails to produce valid numbers (which it should handle internally).
    """
    try:
        num_a = sanitize_input(a)
        num_b = sanitize_input(b)

        if num_b == 0:
            return 0.0
        
        result = num_a / num_b
        return round(result, 2)
    except (ValueError, TypeError):
        # This block catches potential issues during sanitization or if num_a/num_b aren't
        # convertible to float, though sanitize_input is expected to handle these.
        return 0.0