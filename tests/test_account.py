"""Tests for account and position functions."""

import pytest


class TestGetAccountInfo:
    """Tests for get_account_info function."""

    async def test_get_account_info_success(self, server, mock_trading_client):
        """Test successful account info retrieval."""
        # Get the registered tool function
        tools = server.app._tool_manager._tools
        get_account_info = tools["get_account_info"].fn

        result = await get_account_info()

        assert result.success is True
        assert result.data is not None
        assert result.data.cash == 100000.0
        assert result.data.buying_power == 200000.0
        assert result.data.portfolio_value == 150000.0
        assert result.data.equity == 150000.0
        assert result.data.daytrade_count == 2
        mock_trading_client.get_account.assert_called_once()

    async def test_get_account_info_error(self, server, mock_trading_client):
        """Test error handling in account info retrieval."""
        mock_trading_client.get_account.side_effect = Exception("API Error")

        tools = server.app._tool_manager._tools
        get_account_info = tools["get_account_info"].fn

        result = await get_account_info()

        assert result.success is False
        assert "API Error" in result.error


class TestGetPositions:
    """Tests for get_positions function."""

    async def test_get_positions_success(self, server, mock_trading_client):
        """Test successful positions retrieval."""
        tools = server.app._tool_manager._tools
        get_positions = tools["get_positions"].fn

        result = await get_positions()

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0].symbol == "AAPL"
        assert result.data[0].quantity == 100.0
        assert result.data[0].side == "long"
        assert result.data[0].unrealized_pl == 2500.0
        mock_trading_client.get_all_positions.assert_called_once()

    async def test_get_positions_empty(self, server, mock_trading_client):
        """Test when no positions exist."""
        mock_trading_client.get_all_positions.return_value = []

        tools = server.app._tool_manager._tools
        get_positions = tools["get_positions"].fn

        result = await get_positions()

        assert result.success is True
        assert result.data == []

    async def test_get_positions_error(self, server, mock_trading_client):
        """Test error handling in positions retrieval."""
        mock_trading_client.get_all_positions.side_effect = Exception("API Error")

        tools = server.app._tool_manager._tools
        get_positions = tools["get_positions"].fn

        result = await get_positions()

        assert result.success is False
        assert "API Error" in result.error


class TestGetOrder:
    """Tests for get_order function (single order lookup)."""

    async def test_get_order_success(self, server, mock_trading_client, mock_order):
        """Test successful single order retrieval."""
        mock_trading_client.get_order_by_id.return_value = mock_order

        tools = server.app._tool_manager._tools
        get_order = tools["get_order"].fn

        result = await get_order(order_id="test-order-id")

        assert result.success is True
        assert result.data is not None
        assert result.data.symbol == "AAPL"
        assert result.data.qty == 10.0
        mock_trading_client.get_order_by_id.assert_called_once_with("test-order-id")

    async def test_get_order_not_found(self, server, mock_trading_client):
        """Test when order is not found."""
        mock_trading_client.get_order_by_id.side_effect = Exception("Order not found")

        tools = server.app._tool_manager._tools
        get_order = tools["get_order"].fn

        result = await get_order(order_id="invalid-id")

        assert result.success is False
        assert "not found" in result.error.lower()


class TestGetOrders:
    """Tests for get_orders function."""

    async def test_get_orders_success(self, server, mock_trading_client):
        """Test successful orders retrieval."""
        tools = server.app._tool_manager._tools
        get_orders = tools["get_orders"].fn

        result = await get_orders()

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0].symbol == "AAPL"
        assert result.data[0].qty == 10.0
        mock_trading_client.get_orders.assert_called_once()

    async def test_get_orders_with_filters(self, server, mock_trading_client):
        """Test orders retrieval with status and symbol filters."""
        tools = server.app._tool_manager._tools
        get_orders = tools["get_orders"].fn

        result = await get_orders(status="open", limit=50, symbols="AAPL,MSFT")

        assert result.success is True
        # Verify the request was made with correct parameters
        call_args = mock_trading_client.get_orders.call_args
        request = call_args[0][0]
        assert request.status == "open"
        assert request.limit == 50
        assert request.symbols == ["AAPL", "MSFT"]

    async def test_get_orders_error(self, server, mock_trading_client):
        """Test error handling in orders retrieval."""
        mock_trading_client.get_orders.side_effect = Exception("API Error")

        tools = server.app._tool_manager._tools
        get_orders = tools["get_orders"].fn

        result = await get_orders()

        assert result.success is False
        assert "API Error" in result.error


class TestGetPortfolioHistory:
    """Tests for get_portfolio_history function."""

    async def test_get_portfolio_history_success(self, server, mock_trading_client):
        """Test successful portfolio history retrieval."""
        tools = server.app._tool_manager._tools
        get_portfolio_history = tools["get_portfolio_history"].fn

        result = await get_portfolio_history()

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 2
        assert result.data[0]["equity"] == 150000.0
        assert result.data[1]["profit_loss"] == 1000.0

    async def test_get_portfolio_history_with_params(self, server, mock_trading_client):
        """Test portfolio history with custom parameters."""
        tools = server.app._tool_manager._tools
        get_portfolio_history = tools["get_portfolio_history"].fn

        result = await get_portfolio_history(period="1Y", timeframe="1D", extended_hours=True)

        assert result.success is True
        call_args = mock_trading_client.get_portfolio_history.call_args
        request = call_args[0][0]
        assert request.period == "1Y"
        assert request.timeframe == "1D"
        assert request.extended_hours is True

    async def test_get_portfolio_history_error(self, server, mock_trading_client):
        """Test error handling in portfolio history retrieval."""
        mock_trading_client.get_portfolio_history.side_effect = Exception("API Error")

        tools = server.app._tool_manager._tools
        get_portfolio_history = tools["get_portfolio_history"].fn

        result = await get_portfolio_history()

        assert result.success is False
        assert "API Error" in result.error
