# Live Trading API Configuration

This document describes how to configure real-time market data sources and trading modes.

## Configuration Structure

Add the following to your config file:

```json
{
  "data_source": {
    "price": "local",     // local, alpaca, yahoo
    "search": "local",    // local, jina
    "news": "local"       // local, jina
  },
  "trading_mode": "simulation"  // simulation, paper, live
}
```

## Data Sources

### Price Data

| Source | Market | Real-time | API Key Required |
|--------|--------|-----------|-----------------|
| `local` | All | No | No |
| `alpaca` | US stocks | Yes | ALPACA_API_KEY, ALPACA_API_SECRET |
| `yahoo` | US stocks | Delayed (15min) | No |

### Trading Modes

| Mode | Description |
|------|-------------|
| `simulation` | Use local data, simulated trading (default) |
| `paper` | Use real-time data, simulated trading with paper money |
| `live` | Use real-time data, real money trading |

## API Setup

### Alpaca (US Stocks)

1. Sign up at https://alpaca.markets/
2. Get your API keys from the dashboard
3. Set environment variables:

```bash
export ALPACA_API_KEY="your_api_key"
export ALPACA_API_SECRET="your_api_secret"
export ALPACA_BASE_URL="https://paper-api.alpaca.markets"  # for paper trading
# or
export ALPACA_BASE_URL="https://api.alpaca.markets"  # for live trading
```

Or create a `.env` file:

```env
ALPACA_API_KEY=your_api_key
ALPACA_API_SECRET=your_api_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

### Yahoo Finance (Free, Delayed)

No API key required. Data is delayed by 15 minutes.

```json
{
  "data_source": {
    "price": "yahoo"
  }
}
```

## Example Configurations

### Local Simulation (Default)

```json
{
  "data_source": {
    "price": "local",
    "search": "local",
    "news": "local"
  },
  "trading_mode": "simulation"
}
```

### Paper Trading with Alpaca

```json
{
  "data_source": {
    "price": "alpaca",
    "search": "local",
    "news": "local"
  },
  "trading_mode": "paper"
}
```

### Live Trading with Alpaca

```json
{
  "data_source": {
    "price": "alpaca",
    "search": "local",
    "news": "local"
  },
  "trading_mode": "live"
}
```

## Environment Variables

Create a `.env` file in the project root:

```env
# Alpaca API (for US stocks)
ALPACA_API_KEY=your_api_key
ALPACA_API_SECRET=your_api_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Tushare Pro (for China A-shares) - Coming soon
TUSHARE_TOKEN=your_token

# Jina AI Search (for market news) - Coming soon
JINA_API_KEY=your_jina_key
```

## Supported Markets

| Market | Local Data | Alpaca | Yahoo | Tushare |
|--------|------------|--------|-------|---------|
| US Stocks | ✅ | ✅ | ✅ | ❌ |
| A-Shares | ✅ | ❌ | ❌ | ✅ (coming soon) |
| Crypto | ✅ | ❌ | ❌ | ❌ |

## Error Handling

If the configured API is unavailable, the system will fall back to local data:

```
[Warning] Alpaca API credentials not found. Falling back to local data.
```

## Next Steps

- [ ] Add Tushare Pro support for China A-shares
- [ ] Add CCXT support for cryptocurrency exchanges
- [ ] Add support for Interactive Brokers
