"""Small response adapters shared by FastAPI route modules."""
import json


def parse_result(value):
    """Convert existing MCP-era function results into JSON when possible."""
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {"message": value}
