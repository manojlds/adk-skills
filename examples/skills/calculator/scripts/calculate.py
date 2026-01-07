#!/usr/bin/env python3
"""Simple calculator script for demonstration."""

import sys


def calculate(a: float, b: float, operation: str) -> float:
    """Perform a calculation."""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")


if __name__ == "__main__":
    # Simple command-line interface
    if len(sys.argv) != 4:
        print("Usage: calculate.py <number1> <number2> <operation>")
        print("Operations: add, subtract, multiply, divide")
        sys.exit(1)

    try:
        num1 = float(sys.argv[1])
        num2 = float(sys.argv[2])
        op = sys.argv[3]

        result = calculate(num1, num2, op)
        print(f"Result: {result}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
