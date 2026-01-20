# Alpaca MCP Server

An MCP (Model Context Protocol) server that provides trading and market data tools for the [Alpaca](https://alpaca.markets/) brokerage API.

## Features

### Account & Portfolio
- **get_account_info** - Account balance, buying power, equity, margin info
- **get_positions** - Current stock positions with P&L
- **get_portfolio_history** - Historical portfolio performance

### Orders

#### Basic Order Types
- **get_orders** - Order history with filtering
- **get_order** - Get a specific order by ID
- **place_market_order** - Execute at best available price (immediate)
- **place_limit_order** - Execute at specified price or better (or not at all)
- **place_stop_order** - Trigger market order when stop price hit (guarantees fill)
- **place_stop_limit_order** - Trigger limit order when stop price hit (guarantees max price)
- **place_trailing_stop_order** - Dynamic stop that follows price movement
- **cancel_order** - Cancel pending orders

#### Protective Order Strategies
Use these to automatically protect positions with both profit targets AND stop losses:

- **place_bracket_order** - For NEW positions: Entry + take profit + stop loss (3 orders)
  - Use when entering a position and want automatic protection
  - Example: Buy at $175, take profit at $185, stop loss at $170

- **place_oco_order** - For EXISTING positions: Take profit + stop loss (2 orders)
  - Use when you already own shares and want to add protection
  - Example: Already own shares, exit at $185 (profit) OR $170 (loss), whichever comes first

### Position Management
- **close_position** - Close all or part of a position
- **close_all_positions** - Close all open positions (emergency exit)

### Market Data
- **get_latest_quotes** - Real-time bid/ask quotes
- **get_stock_bars** - Historical OHLCV data

### Options Trading
- **get_option_contracts** - Search option chains
- **get_option_contract** - Get specific contract details
- **get_option_positions** - Current option positions
- **place_option_order** - Single-leg option orders
- **place_multi_leg_option_order** - Spreads, straddles, etc.
- **exercise_option_position** - Exercise option contracts

## Installation

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone the repository
git clone <repository-url>
cd alpaca_mcp

# Install dependencies
uv sync

# Install with dev dependencies (for testing)
uv sync --extra dev
```

## Configuration

Set the following environment variables:

```bash
export ALPACA_API_KEY="your-api-key"
export ALPACA_SECRET_KEY="your-secret-key"
export ALPACA_PAPER="true"  # Use paper trading (default: true)
```

Get your API keys from the [Alpaca Dashboard](https://app.alpaca.markets/).

## Usage

### Running the Server

```bash
# Using the launcher (cross-platform)
python launch.py

# Or directly with uv
uv run alpaca-mcp-server

# With SSE transport
uv run alpaca-mcp-server --sse

# With streamable HTTP transport
uv run alpaca-mcp-server --streamable
```

### MCP Client Configuration

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "alpaca": {
      "command": "python",
      "args": ["/path/to/alpaca_mcp/launch.py"],
      "env": {
        "ALPACA_API_KEY": "your-api-key",
        "ALPACA_SECRET_KEY": "your-secret-key",
        "ALPACA_PAPER": "true"
      }
    }
  }
}
```

## Examples

### Place a Bracket Order

Buy 10 shares of AAPL with automatic take profit at $180 and stop loss at $165:

```json
{
  "tool": "place_bracket_order",
  "arguments": {
    "symbol": "AAPL",
    "qty": 10,
    "side": "buy",
    "take_profit_limit_price": 180.00,
    "stop_loss_stop_price": 165.00,
    "entry_type": "limit",
    "entry_limit_price": 170.00
  }
}
```

### Place an Option Spread

Buy a vertical call spread:

```json
{
  "tool": "place_multi_leg_option_order",
  "arguments": {
    "legs": [
      {
        "symbol": "AAPL240119C00175000",
        "ratio_qty": 1,
        "side": "buy",
        "position_intent": "buy_to_open"
      },
      {
        "symbol": "AAPL240119C00180000",
        "ratio_qty": 1,
        "side": "sell",
        "position_intent": "sell_to_open"
      }
    ],
    "order_type": "limit",
    "limit_price": 2.50
  }
}
```

### Get Historical Data

```json
{
  "tool": "get_stock_bars",
  "arguments": {
    "symbols": "AAPL,MSFT",
    "timeframe": "1Day",
    "start": "2024-01-01",
    "end": "2024-01-31",
    "limit": 100
  }
}
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest --cov=server --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_orders.py

# Run specific test
uv run pytest tests/test_orders.py::TestPlaceBracketOrder -v
```

## Project Structure

```
alpaca_mcp/
├── server.py           # Main MCP server implementation
├── launch.py           # Cross-platform launcher
├── pyproject.toml      # Project configuration
├── shared/
│   ├── __init__.py
│   └── types.py        # Pydantic models for requests/responses
└── tests/
    ├── conftest.py     # Test fixtures
    ├── test_account.py
    ├── test_orders.py
    ├── test_market_data.py
    └── test_options.py
```

## License

MIT
