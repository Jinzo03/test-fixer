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

def process_data(a, b):
    # BUG: Doesn't handle ZeroDivisionError or format outputs
    num_a = sanitize_input(a)
    num_b = sanitize_input(b)
    return num_a / num_b