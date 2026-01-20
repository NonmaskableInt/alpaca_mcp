"""Tests for options trading functions."""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4


class TestGetOptionContracts:
    """Tests for get_option_contracts function."""

    async def test_get_option_contracts_success(self, server, mock_trading_client, mock_option_contract):
        """Test successful option contracts retrieval."""
        tools = server.app._tool_manager._tools
        get_option_contracts = tools["get_option_contracts"].fn

        result = await get_option_contracts(underlying_symbols="AAPL")

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0].symbol == "AAPL240119C00175000"
        assert result.data[0].underlying_symbol == "AAPL"
        assert result.data[0].strike_price == "175.00"

    async def test_get_option_contracts_with_filters(self, server, mock_trading_client):
        """Test option contracts with filtering."""
        tools = server.app._tool_manager._tools
        get_option_contracts = tools["get_option_contracts"].fn

        result = await get_option_contracts(
            underlying_symbols="AAPL",
            expiration_date="2024-01-19",
            contract_type="call",
            strike_price_gte="170",
            strike_price_lte="180"
        )

        assert result.success is True
        call_args = mock_trading_client.get_option_contracts.call_args
        request = call_args[0][0]
        assert request.underlying_symbols == ["AAPL"]
        assert request.expiration_date == "2024-01-19"

    async def test_get_option_contracts_with_date_range(self, server, mock_trading_client):
        """Test option contracts with expiration date range."""
        tools = server.app._tool_manager._tools
        get_option_contracts = tools["get_option_contracts"].fn

        result = await get_option_contracts(
            underlying_symbols="AAPL",
            expiration_date_gte="2024-01-01",
            expiration_date_lte="2024-03-31"
        )

        assert result.success is True
        call_args = mock_trading_client.get_option_contracts.call_args
        request = call_args[0][0]
        assert request.expiration_date_gte == "2024-01-01"
        assert request.expiration_date_lte == "2024-03-31"

    async def test_get_option_contracts_empty(self, server, mock_trading_client):
        """Test when no contracts are found."""
        contracts_response = MagicMock()
        contracts_response.option_contracts = []
        mock_trading_client.get_option_contracts.return_value = contracts_response

        tools = server.app._tool_manager._tools
        get_option_contracts = tools["get_option_contracts"].fn

        result = await get_option_contracts(underlying_symbols="ZZZZZ")

        assert result.success is True
        assert result.data == []

    async def test_get_option_contracts_error(self, server, mock_trading_client):
        """Test error handling in contracts retrieval."""
        mock_trading_client.get_option_contracts.side_effect = Exception("API Error")

        tools = server.app._tool_manager._tools
        get_option_contracts = tools["get_option_contracts"].fn

        result = await get_option_contracts(underlying_symbols="AAPL")

        assert result.success is False
        assert "API Error" in result.error


class TestGetOptionContract:
    """Tests for get_option_contract function."""

    async def test_get_option_contract_success(self, server, mock_trading_client, mock_option_contract):
        """Test getting a specific option contract."""
        tools = server.app._tool_manager._tools
        get_option_contract = tools["get_option_contract"].fn

        result = await get_option_contract(symbol="AAPL240119C00175000")

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0].symbol == "AAPL240119C00175000"

    async def test_get_option_contract_not_found(self, server, mock_trading_client):
        """Test when contract is not found."""
        mock_trading_client.get_option_contract.return_value = None

        tools = server.app._tool_manager._tools
        get_option_contract = tools["get_option_contract"].fn

        result = await get_option_contract(symbol="INVALID")

        assert result.success is False
        assert "No contract found" in result.error

    async def test_get_option_contract_error(self, server, mock_trading_client):
        """Test error handling in contract retrieval."""
        mock_trading_client.get_option_contract.side_effect = Exception("API Error")

        tools = server.app._tool_manager._tools
        get_option_contract = tools["get_option_contract"].fn

        result = await get_option_contract(symbol="AAPL240119C00175000")

        assert result.success is False
        assert "API Error" in result.error


class TestGetOptionPositions:
    """Tests for get_option_positions function."""

    async def test_get_option_positions_success(self, server, mock_trading_client, mock_option_position):
        """Test successful option positions retrieval."""
        mock_trading_client.get_all_positions.return_value = [mock_option_position]

        tools = server.app._tool_manager._tools
        get_option_positions = tools["get_option_positions"].fn

        result = await get_option_positions()

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0].symbol == "AAPL240119C00175000"
        assert result.data[0].quantity == 10.0

    async def test_get_option_positions_filters_stocks(self, server, mock_trading_client, mock_position):
        """Test that stock positions are filtered out."""
        # mock_position has asset_class = "us_equity"
        mock_trading_client.get_all_positions.return_value = [mock_position]

        tools = server.app._tool_manager._tools
        get_option_positions = tools["get_option_positions"].fn

        result = await get_option_positions()

        assert result.success is True
        assert result.data == []  # Stock position should be filtered out

    async def test_get_option_positions_empty(self, server, mock_trading_client):
        """Test when no option positions exist."""
        mock_trading_client.get_all_positions.return_value = []

        tools = server.app._tool_manager._tools
        get_option_positions = tools["get_option_positions"].fn

        result = await get_option_positions()

        assert result.success is True
        assert result.data == []

    async def test_get_option_positions_error(self, server, mock_trading_client):
        """Test error handling in option positions retrieval."""
        mock_trading_client.get_all_positions.side_effect = Exception("API Error")

        tools = server.app._tool_manager._tools
        get_option_positions = tools["get_option_positions"].fn

        result = await get_option_positions()

        assert result.success is False
        assert "API Error" in result.error


class TestPlaceOptionOrder:
    """Tests for place_option_order function."""

    async def test_place_option_order_market(self, server, mock_trading_client, mock_order):
        """Test placing a market option order."""
        mock_order.order_type = MagicMock(value="market")

        tools = server.app._tool_manager._tools
        place_option_order = tools["place_option_order"].fn

        result = await place_option_order(
            symbol="AAPL240119C00175000",
            qty=1,
            side="buy",
            position_intent="buy_to_open"
        )

        assert result.success is True
        assert result.data["symbol"] == "AAPL"
        mock_trading_client.submit_order.assert_called_once()

    async def test_place_option_order_limit(self, server, mock_trading_client, mock_order):
        """Test placing a limit option order."""
        mock_order.order_type = MagicMock(value="limit")
        mock_order.limit_price = "5.00"

        tools = server.app._tool_manager._tools
        place_option_order = tools["place_option_order"].fn

        result = await place_option_order(
            symbol="AAPL240119C00175000",
            qty=1,
            side="buy",
            position_intent="buy_to_open",
            order_type="limit",
            limit_price=5.00
        )

        assert result.success is True
        assert result.data["limit_price"] == 5.0

    async def test_place_option_order_limit_missing_price(self, server):
        """Test limit order fails without price."""
        tools = server.app._tool_manager._tools
        place_option_order = tools["place_option_order"].fn

        result = await place_option_order(
            symbol="AAPL240119C00175000",
            qty=1,
            side="buy",
            position_intent="buy_to_open",
            order_type="limit"
        )

        assert result.success is False
        assert "Limit price required" in result.error

    async def test_place_option_order_invalid_intent(self, server):
        """Test order fails with invalid position intent."""
        tools = server.app._tool_manager._tools
        place_option_order = tools["place_option_order"].fn

        result = await place_option_order(
            symbol="AAPL240119C00175000",
            qty=1,
            side="buy",
            position_intent="invalid_intent"
        )

        assert result.success is False
        assert "Invalid position_intent" in result.error

    async def test_place_option_order_all_intents(self, server, mock_trading_client, mock_order):
        """Test all valid position intents."""
        tools = server.app._tool_manager._tools
        place_option_order = tools["place_option_order"].fn

        intents = ["buy_to_open", "buy_to_close", "sell_to_open", "sell_to_close"]
        sides = ["buy", "buy", "sell", "sell"]

        for intent, side in zip(intents, sides):
            result = await place_option_order(
                symbol="AAPL240119C00175000",
                qty=1,
                side=side,
                position_intent=intent
            )
            assert result.success is True


class TestPlaceMultiLegOptionOrder:
    """Tests for place_multi_leg_option_order function."""

    async def test_multi_leg_order_spread(self, server, mock_trading_client, mock_order):
        """Test placing a vertical spread."""
        tools = server.app._tool_manager._tools
        place_multi_leg_option_order = tools["place_multi_leg_option_order"].fn

        legs = [
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
        ]

        result = await place_multi_leg_option_order(legs=legs)

        assert result.success is True
        assert result.data["order_class"] == "multi_leg"
        assert result.data["legs"] == 2

    async def test_multi_leg_order_with_limit(self, server, mock_trading_client, mock_order):
        """Test multi-leg order with limit price."""
        mock_order.limit_price = "1.50"

        tools = server.app._tool_manager._tools
        place_multi_leg_option_order = tools["place_multi_leg_option_order"].fn

        legs = [
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
        ]

        result = await place_multi_leg_option_order(
            legs=legs,
            order_type="limit",
            limit_price=1.50
        )

        assert result.success is True
        assert result.data["limit_price"] == 1.5

    async def test_multi_leg_order_empty_legs(self, server):
        """Test multi-leg order fails with empty legs."""
        tools = server.app._tool_manager._tools
        place_multi_leg_option_order = tools["place_multi_leg_option_order"].fn

        result = await place_multi_leg_option_order(legs=[])

        assert result.success is False
        assert "At least one leg is required" in result.error

    async def test_multi_leg_order_invalid_intent(self, server):
        """Test multi-leg order fails with invalid intent."""
        tools = server.app._tool_manager._tools
        place_multi_leg_option_order = tools["place_multi_leg_option_order"].fn

        legs = [
            {
                "symbol": "AAPL240119C00175000",
                "ratio_qty": 1,
                "side": "buy",
                "position_intent": "invalid"
            }
        ]

        result = await place_multi_leg_option_order(legs=legs)

        assert result.success is False
        assert "Invalid position_intent in leg 0" in result.error

    async def test_multi_leg_order_limit_missing_price(self, server):
        """Test multi-leg limit order fails without price."""
        tools = server.app._tool_manager._tools
        place_multi_leg_option_order = tools["place_multi_leg_option_order"].fn

        legs = [
            {
                "symbol": "AAPL240119C00175000",
                "ratio_qty": 1,
                "side": "buy",
                "position_intent": "buy_to_open"
            }
        ]

        result = await place_multi_leg_option_order(legs=legs, order_type="limit")

        assert result.success is False
        assert "Limit price required" in result.error


class TestExerciseOptionPosition:
    """Tests for exercise_option_position function."""

    async def test_exercise_option_success(self, server, mock_trading_client, mock_option_position):
        """Test exercising an option position."""
        mock_trading_client.get_all_positions.return_value = [mock_option_position]
        mock_trading_client.exercise_options_position.return_value = None

        tools = server.app._tool_manager._tools
        exercise_option_position = tools["exercise_option_position"].fn

        result = await exercise_option_position(symbol="AAPL240119C00175000")

        assert result.success is True
        assert result.data["symbol"] == "AAPL240119C00175000"
        assert result.data["exercised_qty"] == 10.0
        mock_trading_client.exercise_options_position.assert_called_once()

    async def test_exercise_option_partial(self, server, mock_trading_client, mock_option_position):
        """Test exercising partial option position."""
        mock_trading_client.get_all_positions.return_value = [mock_option_position]
        mock_trading_client.exercise_options_position.return_value = None

        tools = server.app._tool_manager._tools
        exercise_option_position = tools["exercise_option_position"].fn

        result = await exercise_option_position(symbol="AAPL240119C00175000", qty=5)

        assert result.success is True
        assert result.data["exercised_qty"] == 5

    async def test_exercise_option_not_found(self, server, mock_trading_client):
        """Test exercising non-existent position."""
        mock_trading_client.get_all_positions.return_value = []

        tools = server.app._tool_manager._tools
        exercise_option_position = tools["exercise_option_position"].fn

        result = await exercise_option_position(symbol="INVALID")

        assert result.success is False
        assert "No position found" in result.error

    async def test_exercise_option_error(self, server, mock_trading_client, mock_option_position):
        """Test error handling during exercise."""
        mock_trading_client.get_all_positions.return_value = [mock_option_position]
        mock_trading_client.exercise_options_position.side_effect = Exception("Exercise failed")

        tools = server.app._tool_manager._tools
        exercise_option_position = tools["exercise_option_position"].fn

        result = await exercise_option_position(symbol="AAPL240119C00175000")

        assert result.success is False
        assert "Exercise failed" in result.error
