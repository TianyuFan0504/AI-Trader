---
name: math-skill
description: Basic mathematical operations for calculations. Use for arithmetic, multiplication, division, and any numerical computations needed during analysis.
---

# Math Skill

## Overview
This skill provides basic mathematical operations for trading calculations.

## Available Tools
- `add(a, b)` - Add two numbers
- `multiply(a, b)` - Multiply two numbers

## Usage Examples

### Calculate position size
```python
total_capital = 10000
risk_per_trade = 0.02
position_value = multiply(total_capital, risk_per_trade)
```

### Calculate portfolio metrics
```python
portfolio_value = 50000
weight = 0.25
allocation = multiply(portfolio_value, weight)
```

## Guidelines
- Use these tools for any numerical calculations
- Always verify calculations before making trading decisions
- Use appropriate precision for financial calculations
