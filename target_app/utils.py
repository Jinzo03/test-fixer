def sanitize_input(val) -> float:
    """Converts input values to float. Raises ValueError on invalid inputs."""
    if val is None:
        raise ValueError("Input cannot be None")
    
    if isinstance(val, (int, float)):
        return float(val)
    
    if isinstance(val, str):
        cleaned = val.strip().replace("$", "").replace(",", "")
        if not cleaned:
            raise ValueError("Empty string value")
        return float(cleaned)
    
    raise ValueError(f"Unsupported type: {type(val)}")