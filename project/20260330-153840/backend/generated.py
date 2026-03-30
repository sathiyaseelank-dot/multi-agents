# Mock backend implementation
def process(data: dict) -> dict:
    """Process input data and return result."""
    return {"status": "ok", "data": data}
def validate(data: dict) -> bool:
    """Validate input data."""
    return bool(data)
