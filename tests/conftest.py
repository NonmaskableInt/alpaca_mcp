"""Pytest fixtures for Alpaca MCP Server tests."""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


# Mock environment variables before importing server
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set required environment variables for all tests."""
    monkeypatch.setenv("ALPACA_API_KEY", "test_api_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test_secret_key")
    monkeypatch.setenv("ALPACA_PAPER", "true")


@pytest.fixture
def mock_account():
    """Create a mock Alpaca account object."""
    account = MagicMock()
    account.id = uuid4()
    account.cash = "100000.00"
    account.buying_power = "200000.00"
    account.portfolio_value = "150000.00"
    account.equity = "150000.00"
    account.long_market_value = "50000.00"
    account.short_market_value = "0.00"
    account.initial_margin = "25000.00"
    account.maintenance_margin = "15000.00"
    account.last_equity = "148000.00"
    account.daytrade_count = 2
    return account


@pytest.fixture
def mock_position():
    """Create a mock Alpaca position object."""
    position = MagicMock()
    position.symbol = "AAPL"
    position.qty = "100"
    position.side = MagicMock(value="long")
    position.market_value = "17500.00"
    position.cost_basis = "15000.00"
    position.unrealized_pl = "2500.00"
    position.unrealized_plpc = "0.1667"
    position.current_price = "175.00"
    position.qty_available = "100"
    position.asset_class = "us_equity"
    return position


@pytest.fixture
def mock_option_position():
    """Create a mock Alpaca option position object."""
    position = MagicMock()
    position.symbol = "AAPL240119C00175000"
    position.qty = "10"
    position.side = MagicMock(value="long")
    position.market_value = "5000.00"
    position.cost_basis = "4000.00"
    position.unrealized_pl = "1000.00"
    position.unrealized_plpc = "0.25"
    position.current_price = "5.00"
    position.qty_available = "10"
    position.asset_class = "us_option"
    return position


@pytest.fixture
def mock_order():
    """Create a mock Alpaca order object."""
    order = MagicMock()
    order.id = uuid4()
    order.symbol = "AAPL"
    order.qty = "10"
    order.side = MagicMock(value="buy")
    order.order_type = MagicMock(value="market")
    order.status = MagicMock(value="filled")
    order.submitted_at = datetime.now(timezone.utc)
    order.filled_at = datetime.now(timezone.utc)
    order.filled_qty = "10"
    order.filled_avg_price = "175.00"
    order.limit_price = None
    order.stop_price = None
    order.trail_percent = None
    order.trail_price = None
    return order


@pytest.fixture
def mock_quote():
    """Create a mock Alpaca quote object."""
    quote = MagicMock()
    quote.bid_price = 174.50
    quote.ask_price = 175.50
    quote.bid_size = 100
    quote.ask_size = 150
    quote.timestamp = datetime.now(timezone.utc)
    return quote


@pytest.fixture
def mock_bar():
    """Create a mock Alpaca bar object."""
    bar = MagicMock()
    bar.timestamp = datetime.now(timezone.utc)
    bar.open = 173.00
    bar.high = 176.00
    bar.low = 172.50
    bar.close = 175.00
    bar.volume = 1000000
    bar.trade_count = 5000
    bar.vwap = 174.50
    return bar


@pytest.fixture
def mock_option_contract():
    """Create a mock Alpaca option contract object."""
    contract = MagicMock()
    contract.symbol = "AAPL240119C00175000"
    contract.underlying_symbol = "AAPL"
    contract.name = "AAPL Jan 19 2024 175 Call"
    contract.status = "active"
    contract.tradable = True
    contract.expiration_date = "2024-01-19"
    contract.root_symbol = "AAPL"
    contract.underlying_asset_id = str(uuid4())
    # Use string values that match the enum expectations
    contract.type = "call"
    contract.style = "american"
    contract.strike_price = "175.00"
    contract.multiplier = "100"
    contract.size = "100"
    contract.open_interest = 1500
    contract.open_interest_date = "2024-01-15"
    contract.close_price = "5.25"
    contract.close_price_date = "2024-01-15"
    return contract


@pytest.fixture
def mock_trading_client(mock_account, mock_position, mock_order, mock_option_contract, mock_option_position):
    """Create a mock TradingClient."""
    client = MagicMock()
    client.get_account.return_value = mock_account
    client.get_all_positions.return_value = [mock_position]
    client.get_orders.return_value = [mock_order]
    client.submit_order.return_value = mock_order
    client.cancel_order_by_id.return_value = None
    client.get_portfolio_history.return_value = MagicMock(
        timestamp=[1705000000, 1705100000],
        equity=[150000.0, 151000.0],
        profit_loss=[0.0, 1000.0],
        profit_loss_pct=[0.0, 0.0067],
    )

    # Option contracts (plural) - returns response with option_contracts list
    contracts_response = MagicMock()
    contracts_response.option_contracts = [mock_option_contract]
    client.get_option_contracts.return_value = contracts_response

    # Option contract (singular) - returns contract directly, not wrapped
    # Configure the mock to NOT have option_contracts attribute
    single_contract = MagicMock(spec=[
        'symbol', 'underlying_symbol', 'name', 'status', 'tradable',
        'expiration_date', 'root_symbol', 'underlying_asset_id', 'type',
        'style', 'strike_price', 'multiplier', 'size', 'open_interest',
        'open_interest_date', 'close_price', 'close_price_date'
    ])
    single_contract.symbol = "AAPL240119C00175000"
    single_contract.underlying_symbol = "AAPL"
    single_contract.name = "AAPL Jan 19 2024 175 Call"
    single_contract.status = "active"
    single_contract.tradable = True
    single_contract.expiration_date = "2024-01-19"
    single_contract.root_symbol = "AAPL"
    single_contract.underlying_asset_id = str(uuid4())
    single_contract.type = "call"
    single_contract.style = "american"
    single_contract.strike_price = "175.00"
    single_contract.multiplier = "100"
    single_contract.size = "100"
    single_contract.open_interest = 1500
    single_contract.open_interest_date = "2024-01-15"
    single_contract.close_price = "5.25"
    single_contract.close_price_date = "2024-01-15"
    client.get_option_contract.return_value = single_contract

    return client


@pytest.fixture
def mock_data_client(mock_quote, mock_bar):
    """Create a mock StockHistoricalDataClient."""
    client = MagicMock()
    client.get_stock_latest_quote.return_value = {"AAPL": mock_quote}

    bars_response = MagicMock()
    bars_response.data = {"AAPL": [mock_bar]}
    client.get_stock_bars.return_value = bars_response

    return client


@pytest.fixture
def server(mock_trading_client, mock_data_client):
    """Create an AlpacaMCPServer with mocked clients."""
    with patch("server.TradingClient", return_value=mock_trading_client), \
         patch("server.StockHistoricalDataClient", return_value=mock_data_client):
        from server import AlpacaMCPServer
        server = AlpacaMCPServer()
        # Replace clients with mocks to ensure they're used
        server.trading_client = mock_trading_client
        server.data_client = mock_data_client
        return server
