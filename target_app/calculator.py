def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b

def process_data(a, b):
    try:
        a_float = float(a)
        b_float = float(b)
        if b_float == 0:
            return 0.0
        result = a_float / b_float
        return round(result, 2)
    except (ValueError, TypeError): # Handle cases where conversion to float fails for non-numeric strings
        return 0.0 # Or raise an appropriate error, but 0.0 seems to be the intended default for error cases based on zero division