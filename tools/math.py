"""
Math tools - Basic arithmetic operations.
"""

from tools import tool


@tool(description="Add two numbers")
def add(a: float, b: float) -> float:
    """Add two numbers (supports int and float).

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return float(a) + float(b)


@tool(description="Multiply two numbers")
def multiply(a: float, b: float) -> float:
    """Multiply two numbers (supports int and float).

    Args:
        a: First number
        b: Second number

    Returns:
        Product of a and b
    """
    return float(a) * float(b)
