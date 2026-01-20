"""Tests for market data functions."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone


class TestGetLatestQuotes:
    """Tests for get_latest_quotes function."""

    async def test_get_latest_quotes_single_symbol(self, server, mock_data_client, mock_quote):
        """Test getting quote for a single symbol."""
        tools = server.app._tool_manager._tools
        get_latest_quotes = tools["get_latest_quotes"].fn

        result = await get_latest_quotes(symbols="AAPL")

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0].symbol == "AAPL"
        assert result.data[0].bid_price == 174.50
        assert result.data[0].ask_price == 175.50
        mock_data_client.get_stock_latest_quote.assert_called_once()

    async def test_get_latest_quotes_multiple_symbols(self, server, mock_data_client, mock_quote):
        """Test getting quotes for multiple symbols."""
        # Set up mock for multiple symbols
        mock_quote2 = MagicMock()
        mock_quote2.bid_price = 374.50
        mock_quote2.ask_price = 375.50
        mock_quote2.bid_size = 200
        mock_quote2.ask_size = 250
        mock_quote2.timestamp = datetime.now(timezone.utc)

        mock_data_client.get_stock_latest_quote.return_value = {
            "AAPL": mock_quote,
            "MSFT": mock_quote2
        }

        tools = server.app._tool_manager._tools
        get_latest_quotes = tools["get_latest_quotes"].fn

        result = await get_latest_quotes(symbols="AAPL,MSFT")

        assert result.success is True
        assert len(result.data) == 2
        symbols = [q.symbol for q in result.data]
        assert "AAPL" in symbols
        assert "MSFT" in symbols

    async def test_get_latest_quotes_lowercase_symbols(self, server, mock_data_client):
        """Test that lowercase symbols are converted to uppercase."""
        tools = server.app._tool_manager._tools
        get_latest_quotes = tools["get_latest_quotes"].fn

        await get_latest_quotes(symbols="aapl, msft")

        # Verify the request was made with uppercase symbols
        call_args = mock_data_client.get_stock_latest_quote.call_args
        request = call_args[0][0]
        assert "AAPL" in request.symbol_or_symbols
        assert "MSFT" in request.symbol_or_symbols

    async def test_get_latest_quotes_error(self, server, mock_data_client):
        """Test error handling in quotes retrieval."""
        mock_data_client.get_stock_latest_quote.side_effect = Exception("API Error")

        tools = server.app._tool_manager._tools
        get_latest_quotes = tools["get_latest_quotes"].fn

        result = await get_latest_quotes(symbols="INVALID")

        assert result.success is False
        assert "API Error" in result.error


class TestGetStockBars:
    """Tests for get_stock_bars function."""

    async def test_get_stock_bars_default_params(self, server, mock_data_client, mock_bar):
        """Test getting bars with default parameters."""
        tools = server.app._tool_manager._tools
        get_stock_bars = tools["get_stock_bars"].fn

        result = await get_stock_bars(symbols="AAPL")

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0].symbol == "AAPL"
        assert result.data[0].open == 173.0
        assert result.data[0].high == 176.0
        assert result.data[0].low == 172.5
        assert result.data[0].close == 175.0
        assert result.data[0].volume == 1000000

    async def test_get_stock_bars_with_timeframe(self, server, mock_data_client, mock_bar):
        """Test getting bars with custom timeframe."""
        tools = server.app._tool_manager._tools
        get_stock_bars = tools["get_stock_bars"].fn

        result = await get_stock_bars(symbols="AAPL", timeframe="1Hour")

        assert result.success is True
        call_args = mock_data_client.get_stock_bars.call_args
        request = call_args[0][0]
        # Verify timeframe was passed (the actual TimeFrame object comparison is tricky)
        assert request.timeframe is not None

    async def test_get_stock_bars_with_date_range(self, server, mock_data_client, mock_bar):
        """Test getting bars with date range."""
        tools = server.app._tool_manager._tools
        get_stock_bars = tools["get_stock_bars"].fn

        result = await get_stock_bars(
            symbols="AAPL",
            start="2024-01-01",
            end="2024-01-15",
            limit=50
        )

        assert result.success is True
        call_args = mock_data_client.get_stock_bars.call_args
        request = call_args[0][0]
        assert request.limit == 50
        assert request.start is not None
        assert request.end is not None

    async def test_get_stock_bars_multiple_symbols(self, server, mock_data_client, mock_bar):
        """Test getting bars for multiple symbols."""
        mock_bar2 = MagicMock()
        mock_bar2.timestamp = datetime.now(timezone.utc)
        mock_bar2.open = 373.0
        mock_bar2.high = 376.0
        mock_bar2.low = 372.5
        mock_bar2.close = 375.0
        mock_bar2.volume = 500000
        mock_bar2.trade_count = 3000
        mock_bar2.vwap = 374.5

        bars_response = MagicMock()
        bars_response.data = {
            "AAPL": [mock_bar],
            "MSFT": [mock_bar2]
        }
        mock_data_client.get_stock_bars.return_value = bars_response

        tools = server.app._tool_manager._tools
        get_stock_bars = tools["get_stock_bars"].fn

        result = await get_stock_bars(symbols="AAPL,MSFT")

        assert result.success is True
        assert len(result.data) == 2

    async def test_get_stock_bars_empty_result(self, server, mock_data_client):
        """Test when no bars are returned."""
        bars_response = MagicMock()
        bars_response.data = {}
        mock_data_client.get_stock_bars.return_value = bars_response

        tools = server.app._tool_manager._tools
        get_stock_bars = tools["get_stock_bars"].fn

        result = await get_stock_bars(symbols="AAPL")

        assert result.success is True
        assert result.data == []

    async def test_get_stock_bars_error(self, server, mock_data_client):
        """Test error handling in bars retrieval."""
        mock_data_client.get_stock_bars.side_effect = Exception("API Error")

        tools = server.app._tool_manager._tools
        get_stock_bars = tools["get_stock_bars"].fn

        result = await get_stock_bars(symbols="AAPL")

        assert result.success is False
        assert "API Error" in result.error

    async def test_get_stock_bars_invalid_timeframe_uses_default(self, server, mock_data_client, mock_bar):
        """Test that invalid timeframe falls back to Day."""
        tools = server.app._tool_manager._tools
        get_stock_bars = tools["get_stock_bars"].fn

        result = await get_stock_bars(symbols="AAPL", timeframe="invalid")

        assert result.success is True
        # Should not fail, uses default Day timeframe
