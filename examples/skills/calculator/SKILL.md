---
name: calculator
description: Perform basic mathematical calculations (add, subtract, multiply, divide)
license: MIT
compatibility: Python 3.9+
---

# Calculator Skill

Use this skill when you need to perform basic mathematical calculations.

## When to Use

- Adding two or more numbers
- Subtracting numbers
- Multiplying numbers
- Dividing numbers
- Any basic arithmetic operation

## Available Operations

- **add**: Add two numbers together
- **subtract**: Subtract second number from first
- **multiply**: Multiply two numbers
- **divide**: Divide first number by second

## Guidelines

1. Check that all inputs are valid numbers
2. For division, ensure divisor is not zero
3. Return results as floating-point numbers for precision

## Examples

```python
# Addition
result = calculate(5, 3, "add")  # Returns 8

# Division
result = calculate(10, 2, "divide")  # Returns 5.0
```

## Scripts Available

- `calculate.py`: Main calculator script
