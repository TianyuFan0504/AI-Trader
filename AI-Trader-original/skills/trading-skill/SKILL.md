---
name: trading-skill
description: Execute stock and cryptocurrency trades. Use for buying and selling positions. Supports US stocks, China A-shares (lot size 100), and crypto. Handles position management and cash accounting.
---

# Trading Skill

## Overview
This skill enables execution of trades for:
- **US stocks**: Any quantity
- **China A-shares**: Lots of 100 shares
- **Cryptocurrency**: Any amount

## Available Tools
- `buy(symbol, amount)` - Buy stocks or crypto
- `sell(symbol, amount)` - Sell stocks or crypto
- `buy_crypto(symbol, amount)` - Buy cryptocurrency
- `sell_crypto(symbol, amount)` - Sell cryptocurrency

## Usage Examples

### Buy US stocks
```python
result = buy(symbol="AAPL", amount=10)
```

### Sell US stocks
```python
result = sell(symbol="AAPL", amount=5)
```

### Buy China A-shares (lot size 100)
```python
result = buy(symbol="600519.SH", amount=100)  # Valid
result = buy(symbol="600519.SH, amount=50)   # Invalid - not a lot
```

### Buy cryptocurrency
```python
result = buy_crypto(symbol="BTC-USDT", amount=0.5)
```

## Return Value
All trade tools return the updated position dictionary:
```python
{
    "AAPL": 10,
    "MSFT": 5,
    "CASH": 9500.00
}
```

## Validation Rules
- Amount must be positive
- China A-shares: multiples of 100 only
- Cannot sell more than held
- Cannot buy without sufficient cash

## Environment
Configure via environment variables:
- `SIGNATURE` - Agent identifier
- `TODAY_DATE` - Trading date (YYYY-MM-DD)
- `LOG_PATH` - Position database path
