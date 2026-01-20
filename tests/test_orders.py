"""Tests for order placement functions."""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4


class TestPlaceMarketOrder:
    """Tests for place_market_order function."""

    async def test_place_market_order_buy(self, server, mock_trading_client, mock_order):
        """Test placing a market buy order."""
        tools = server.app._tool_manager._tools
        place_market_order = tools["place_market_order"].fn

        result = await place_market_order(
            symbol="AAPL",
            qty=10,
            side="buy",
            time_in_force="day"
        )

        assert result.success is True
        assert result.data["symbol"] == "AAPL"
        assert result.data["qty"] == 10.0
        assert result.data["side"] == "buy"
        mock_trading_client.submit_order.assert_called_once()

    async def test_place_market_order_sell(self, server, mock_trading_client, mock_order):
        """Test placing a market sell order."""
        mock_order.side = MagicMock(value="sell")

        tools = server.app._tool_manager._tools
        place_market_order = tools["place_market_order"].fn

        result = await place_market_order(
            symbol="AAPL",
            qty=10,
            side="sell"
        )

        assert result.success is True
        assert result.data["side"] == "sell"

    async def test_place_market_order_error(self, server, mock_trading_client):
        """Test error handling when placing market order fails."""
        mock_trading_client.submit_order.side_effect = Exception("Insufficient funds")

        tools = server.app._tool_manager._tools
        place_market_order = tools["place_market_order"].fn

        result = await place_market_order(symbol="AAPL", qty=10, side="buy")

        assert result.success is False
        assert "Insufficient funds" in result.error


class TestPlaceLimitOrder:
    """Tests for place_limit_order function."""

    async def test_place_limit_order_success(self, server, mock_trading_client, mock_order):
        """Test placing a limit order."""
        mock_order.limit_price = "175.00"
        mock_order.order_type = MagicMock(value="limit")

        tools = server.app._tool_manager._tools
        place_limit_order = tools["place_limit_order"].fn

        result = await place_limit_order(
            symbol="AAPL",
            qty=10,
            side="buy",
            limit_price=175.00
        )

        assert result.success is True
        assert result.data["limit_price"] == 175.0
        mock_trading_client.submit_order.assert_called_once()

    async def test_place_limit_order_with_gtc(self, server, mock_trading_client, mock_order):
        """Test limit order with GTC time in force."""
        mock_order.limit_price = "175.00"

        tools = server.app._tool_manager._tools
        place_limit_order = tools["place_limit_order"].fn

        result = await place_limit_order(
            symbol="AAPL",
            qty=10,
            side="buy",
            limit_price=175.00,
            time_in_force="gtc"
        )

        assert result.success is True


class TestPlaceStopOrder:
    """Tests for place_stop_order function."""

    async def test_place_stop_order_success(self, server, mock_trading_client, mock_order):
        """Test placing a stop order."""
        mock_order.stop_price = "170.00"
        mock_order.order_type = MagicMock(value="stop")

        tools = server.app._tool_manager._tools
        place_stop_order = tools["place_stop_order"].fn

        result = await place_stop_order(
            symbol="AAPL",
            qty=10,
            side="sell",
            stop_price=170.00
        )

        assert result.success is True
        assert result.data["stop_price"] == 170.0

    async def test_place_stop_order_error(self, server, mock_trading_client):
        """Test error handling when placing stop order fails."""
        mock_trading_client.submit_order.side_effect = Exception("Invalid stop price")

        tools = server.app._tool_manager._tools
        place_stop_order = tools["place_stop_order"].fn

        result = await place_stop_order(
            symbol="AAPL",
            qty=10,
            side="sell",
            stop_price=170.00
        )

        assert result.success is False
        assert "Invalid stop price" in result.error


class TestPlaceStopLimitOrder:
    """Tests for place_stop_limit_order function."""

    async def test_place_stop_limit_order_success(self, server, mock_trading_client, mock_order):
        """Test placing a stop-limit order."""
        mock_order.stop_price = "170.00"
        mock_order.limit_price = "169.00"
        mock_order.order_type = MagicMock(value="stop_limit")

        tools = server.app._tool_manager._tools
        place_stop_limit_order = tools["place_stop_limit_order"].fn

        result = await place_stop_limit_order(
            symbol="AAPL",
            qty=10,
            side="sell",
            stop_price=170.00,
            limit_price=169.00
        )

        assert result.success is True
        assert result.data["stop_price"] == 170.0
        assert result.data["limit_price"] == 169.0


class TestPlaceTrailingStopOrder:
    """Tests for place_trailing_stop_order function."""

    async def test_trailing_stop_with_percent(self, server, mock_trading_client, mock_order):
        """Test trailing stop order with percent."""
        mock_order.trail_percent = "5.0"
        mock_order.trail_price = None

        tools = server.app._tool_manager._tools
        place_trailing_stop_order = tools["place_trailing_stop_order"].fn

        result = await place_trailing_stop_order(
            symbol="AAPL",
            qty=10,
            side="sell",
            trail_percent=5.0
        )

        assert result.success is True
        assert result.data["trail_percent"] == 5.0

    async def test_trailing_stop_with_price(self, server, mock_trading_client, mock_order):
        """Test trailing stop order with fixed price."""
        mock_order.trail_percent = None
        mock_order.trail_price = "5.00"

        tools = server.app._tool_manager._tools
        place_trailing_stop_order = tools["place_trailing_stop_order"].fn

        result = await place_trailing_stop_order(
            symbol="AAPL",
            qty=10,
            side="sell",
            trail_price=5.00
        )

        assert result.success is True
        assert result.data["trail_price"] == 5.0

    async def test_trailing_stop_missing_params(self, server):
        """Test trailing stop order fails without trail param."""
        tools = server.app._tool_manager._tools
        place_trailing_stop_order = tools["place_trailing_stop_order"].fn

        result = await place_trailing_stop_order(
            symbol="AAPL",
            qty=10,
            side="sell"
        )

        assert result.success is False
        assert "trail_percent or trail_price must be provided" in result.error

    async def test_trailing_stop_both_params(self, server):
        """Test trailing stop order fails with both trail params."""
        tools = server.app._tool_manager._tools
        place_trailing_stop_order = tools["place_trailing_stop_order"].fn

        result = await place_trailing_stop_order(
            symbol="AAPL",
            qty=10,
            side="sell",
            trail_percent=5.0,
            trail_price=5.0
        )

        assert result.success is False
        assert "Only one of" in result.error


class TestPlaceBracketOrder:
    """Tests for place_bracket_order function."""

    async def test_bracket_order_market_entry(self, server, mock_trading_client, mock_order):
        """Test bracket order with market entry."""
        tools = server.app._tool_manager._tools
        place_bracket_order = tools["place_bracket_order"].fn

        result = await place_bracket_order(
            symbol="AAPL",
            qty=10,
            side="buy",
            take_profit_limit_price=180.00,
            stop_loss_stop_price=165.00
        )

        assert result.success is True
        assert result.data["order_class"] == "bracket"
        assert result.data["take_profit_limit_price"] == 180.00
        assert result.data["stop_loss_stop_price"] == 165.00

    async def test_bracket_order_limit_entry(self, server, mock_trading_client, mock_order):
        """Test bracket order with limit entry."""
        mock_order.limit_price = "175.00"

        tools = server.app._tool_manager._tools
        place_bracket_order = tools["place_bracket_order"].fn

        result = await place_bracket_order(
            symbol="AAPL",
            qty=10,
            side="buy",
            take_profit_limit_price=180.00,
            stop_loss_stop_price=165.00,
            entry_type="limit",
            entry_limit_price=175.00
        )

        assert result.success is True
        assert result.data["entry_type"] == "limit"
        assert result.data["entry_limit_price"] == 175.00

    async def test_bracket_order_with_stop_limit_loss(self, server, mock_trading_client, mock_order):
        """Test bracket order with stop-limit stop loss."""
        tools = server.app._tool_manager._tools
        place_bracket_order = tools["place_bracket_order"].fn

        result = await place_bracket_order(
            symbol="AAPL",
            qty=10,
            side="buy",
            take_profit_limit_price=180.00,
            stop_loss_stop_price=165.00,
            stop_loss_limit_price=164.00
        )

        assert result.success is True
        assert result.data["stop_loss_limit_price"] == 164.00

    async def test_bracket_order_limit_without_price(self, server):
        """Test bracket order fails when limit entry has no price."""
        tools = server.app._tool_manager._tools
        place_bracket_order = tools["place_bracket_order"].fn

        result = await place_bracket_order(
            symbol="AAPL",
            qty=10,
            side="buy",
            take_profit_limit_price=180.00,
            stop_loss_stop_price=165.00,
            entry_type="limit"
        )

        assert result.success is False
        assert "entry_limit_price is required" in result.error


class TestPlaceOCOOrder:
    """Tests for place_oco_order function."""

    async def test_oco_order_success(self, server, mock_trading_client, mock_order):
        """Test placing an OCO order."""
        mock_order.limit_price = "180.00"

        tools = server.app._tool_manager._tools
        place_oco_order = tools["place_oco_order"].fn

        result = await place_oco_order(
            symbol="AAPL",
            qty=10,
            side="sell",
            take_profit_limit_price=180.00,
            stop_loss_stop_price=165.00
        )

        assert result.success is True
        assert result.data["order_class"] == "oco"
        assert result.data["take_profit_limit_price"] == 180.00
        assert result.data["stop_loss_stop_price"] == 165.00

    async def test_oco_order_with_stop_limit(self, server, mock_trading_client, mock_order):
        """Test OCO order with stop-limit loss."""
        mock_order.limit_price = "180.00"

        tools = server.app._tool_manager._tools
        place_oco_order = tools["place_oco_order"].fn

        result = await place_oco_order(
            symbol="AAPL",
            qty=10,
            side="sell",
            take_profit_limit_price=180.00,
            stop_loss_stop_price=165.00,
            stop_loss_limit_price=164.00
        )

        assert result.success is True
        assert result.data["stop_loss_limit_price"] == 164.00


class TestCancelOrder:
    """Tests for cancel_order function."""

    async def test_cancel_order_success(self, server, mock_trading_client):
        """Test successful order cancellation."""
        order_id = str(uuid4())

        tools = server.app._tool_manager._tools
        cancel_order = tools["cancel_order"].fn

        result = await cancel_order(order_id=order_id)

        assert result.success is True
        assert "cancelled successfully" in result.data["message"]
        mock_trading_client.cancel_order_by_id.assert_called_once_with(order_id)

    async def test_cancel_order_not_found(self, server, mock_trading_client):
        """Test cancellation when order not found."""
        mock_trading_client.cancel_order_by_id.side_effect = Exception("Order not found")

        tools = server.app._tool_manager._tools
        cancel_order = tools["cancel_order"].fn

        result = await cancel_order(order_id="invalid-id")

        assert result.success is False
        assert "Order not found" in result.error


class TestClosePosition:
    """Tests for close_position function."""

    async def test_close_position_full(self, server, mock_trading_client, mock_order):
        """Test closing entire position."""
        mock_trading_client.close_position.return_value = mock_order

        tools = server.app._tool_manager._tools
        close_position = tools["close_position"].fn

        result = await close_position(symbol="AAPL")

        assert result.success is True
        assert result.data["symbol"] == "AAPL"
        mock_trading_client.close_position.assert_called_once()

    async def test_close_position_partial_qty(self, server, mock_trading_client, mock_order):
        """Test closing partial position by quantity."""
        mock_trading_client.close_position.return_value = mock_order

        tools = server.app._tool_manager._tools
        close_position = tools["close_position"].fn

        result = await close_position(symbol="AAPL", qty=50)

        assert result.success is True
        call_args = mock_trading_client.close_position.call_args
        assert call_args[0][0] == "AAPL"

    async def test_close_position_partial_percentage(self, server, mock_trading_client, mock_order):
        """Test closing partial position by percentage."""
        mock_trading_client.close_position.return_value = mock_order

        tools = server.app._tool_manager._tools
        close_position = tools["close_position"].fn

        result = await close_position(symbol="AAPL", percentage=50)

        assert result.success is True

    async def test_close_position_both_params_error(self, server):
        """Test error when both qty and percentage provided."""
        tools = server.app._tool_manager._tools
        close_position = tools["close_position"].fn

        result = await close_position(symbol="AAPL", qty=50, percentage=50)

        assert result.success is False
        assert "Only one of" in result.error

    async def test_close_position_invalid_qty(self, server):
        """Test error with invalid quantity."""
        tools = server.app._tool_manager._tools
        close_position = tools["close_position"].fn

        result = await close_position(symbol="AAPL", qty=-10)

        assert result.success is False
        assert "greater than 0" in result.error

    async def test_close_position_invalid_percentage(self, server):
        """Test error with invalid percentage."""
        tools = server.app._tool_manager._tools
        close_position = tools["close_position"].fn

        result = await close_position(symbol="AAPL", percentage=150)

        assert result.success is False
        assert "between 0 and 100" in result.error

    async def test_close_position_not_found(self, server, mock_trading_client):
        """Test closing non-existent position."""
        mock_trading_client.close_position.side_effect = Exception("Position not found")

        tools = server.app._tool_manager._tools
        close_position = tools["close_position"].fn

        result = await close_position(symbol="INVALID")

        assert result.success is False
        assert "Failed to close position" in result.error


class TestCloseAllPositions:
    """Tests for close_all_positions function."""

    async def test_close_all_positions_success(self, server, mock_trading_client, mock_order):
        """Test closing all positions."""
        mock_trading_client.close_all_positions.return_value = [mock_order]

        tools = server.app._tool_manager._tools
        close_all_positions = tools["close_all_positions"].fn

        result = await close_all_positions()

        assert result.success is True
        assert result.data["closed_count"] >= 0
        mock_trading_client.close_all_positions.assert_called_once_with(cancel_orders=False)

    async def test_close_all_positions_with_cancel(self, server, mock_trading_client, mock_order):
        """Test closing all positions and cancelling orders."""
        mock_trading_client.close_all_positions.return_value = [mock_order]

        tools = server.app._tool_manager._tools
        close_all_positions = tools["close_all_positions"].fn

        result = await close_all_positions(cancel_orders=True)

        assert result.success is True
        mock_trading_client.close_all_positions.assert_called_once_with(cancel_orders=True)

    async def test_close_all_positions_empty(self, server, mock_trading_client):
        """Test when no positions to close."""
        mock_trading_client.close_all_positions.return_value = []

        tools = server.app._tool_manager._tools
        close_all_positions = tools["close_all_positions"].fn

        result = await close_all_positions()

        assert result.success is True
        assert result.data["closed_count"] == 0

    async def test_close_all_positions_error(self, server, mock_trading_client):
        """Test error handling when closing all positions fails."""
        mock_trading_client.close_all_positions.side_effect = Exception("API Error")

        tools = server.app._tool_manager._tools
        close_all_positions = tools["close_all_positions"].fn

        result = await close_all_positions()

        assert result.success is False
        assert "Failed to close all positions" in result.error


class TestInputValidation:
    """Tests for input validation across order functions."""

    async def test_market_order_negative_qty(self, server):
        """Test market order fails with negative quantity."""
        tools = server.app._tool_manager._tools
        place_market_order = tools["place_market_order"].fn

        result = await place_market_order(symbol="AAPL", qty=-10, side="buy")

        assert result.success is False
        assert "greater than 0" in result.error

    async def test_market_order_zero_qty(self, server):
        """Test market order fails with zero quantity."""
        tools = server.app._tool_manager._tools
        place_market_order = tools["place_market_order"].fn

        result = await place_market_order(symbol="AAPL", qty=0, side="buy")

        assert result.success is False
        assert "greater than 0" in result.error

    async def test_limit_order_negative_price(self, server):
        """Test limit order fails with negative price."""
        tools = server.app._tool_manager._tools
        place_limit_order = tools["place_limit_order"].fn

        result = await place_limit_order(symbol="AAPL", qty=10, side="buy", limit_price=-100)

        assert result.success is False
        assert "greater than 0" in result.error

    async def test_stop_order_negative_price(self, server):
        """Test stop order fails with negative stop price."""
        tools = server.app._tool_manager._tools
        place_stop_order = tools["place_stop_order"].fn

        result = await place_stop_order(symbol="AAPL", qty=10, side="sell", stop_price=-100)

        assert result.success is False
        assert "greater than 0" in result.error

    async def test_trailing_stop_negative_percent(self, server):
        """Test trailing stop fails with negative trail percent."""
        tools = server.app._tool_manager._tools
        place_trailing_stop_order = tools["place_trailing_stop_order"].fn

        result = await place_trailing_stop_order(symbol="AAPL", qty=10, side="sell", trail_percent=-5)

        assert result.success is False
        assert "greater than 0" in result.error

    async def test_bracket_order_negative_tp(self, server):
        """Test bracket order fails with negative take profit price."""
        tools = server.app._tool_manager._tools
        place_bracket_order = tools["place_bracket_order"].fn

        result = await place_bracket_order(
            symbol="AAPL",
            qty=10,
            side="buy",
            take_profit_limit_price=-180,
            stop_loss_stop_price=165
        )

        assert result.success is False
        assert "greater than 0" in result.error

    async def test_oco_order_negative_sl(self, server):
        """Test OCO order fails with negative stop loss price."""
        tools = server.app._tool_manager._tools
        place_oco_order = tools["place_oco_order"].fn

        result = await place_oco_order(
            symbol="AAPL",
            qty=10,
            side="sell",
            take_profit_limit_price=180,
            stop_loss_stop_price=-165
        )

        assert result.success is False
        assert "greater than 0" in result.error
