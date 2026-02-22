"""Alpaca MCP Server implementation."""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from alpaca.trading import TradingClient
from alpaca.data import StockHistoricalDataClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    StopLimitOrderRequest,
    TrailingStopOrderRequest,
    GetOrdersRequest,
    GetPortfolioHistoryRequest,
    GetOptionContractsRequest,
    OptionLegRequest,
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    OrderType,
    PositionIntent as AlpacaPositionIntent,
    ContractType as AlpacaContractType,
    ExerciseStyle as AlpacaExerciseStyle,
)
from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from mcp.server.fastmcp import FastMCP

from shared.types import (
    AccountInfo,
    Position,
    Order,
    QuoteData,
    BarData,
    OptionContract,
    OptionPosition,
    ContractType,
    MCPResponse,
    AccountResponse,
    PositionsResponse,
    OrdersResponse,
    OrderResponse,
    QuotesResponse,
    BarsResponse,
    OptionContractsResponse,
    OptionPositionsResponse,
)

# Reusable mappings
TIME_IN_FORCE_MAP = {
    "gtc": TimeInForce.GTC,
    "day": TimeInForce.DAY,
    "ioc": TimeInForce.IOC,
    "fok": TimeInForce.FOK,
    "cls": TimeInForce.CLS,
    "opg": TimeInForce.OPG,
}

POSITION_INTENT_MAP = {
    "buy_to_open": AlpacaPositionIntent.BUY_TO_OPEN,
    "buy_to_close": AlpacaPositionIntent.BUY_TO_CLOSE,
    "sell_to_open": AlpacaPositionIntent.SELL_TO_OPEN,
    "sell_to_close": AlpacaPositionIntent.SELL_TO_CLOSE,
}


def validate_order_params(
    qty: Optional[float] = None,
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    trail_price: Optional[float] = None,
) -> Optional[str]:
    """Validate order parameters. Returns error message if invalid, None if valid."""
    if qty is not None and qty <= 0:
        return "Quantity must be greater than 0"
    if limit_price is not None and limit_price <= 0:
        return "Limit price must be greater than 0"
    if stop_price is not None and stop_price <= 0:
        return "Stop price must be greater than 0"
    if trail_price is not None and trail_price <= 0:
        return "Trail price must be greater than 0"
    return None


def parse_option_contract(contract) -> Optional[OptionContract]:
    """Parse an option contract from Alpaca response to OptionContract model."""
    if hasattr(contract, 'symbol'):
        return OptionContract(
            symbol=str(contract.symbol),
            underlying_symbol=str(getattr(contract, 'underlying_symbol', '')),
            name=str(getattr(contract, 'name', '')) if getattr(contract, 'name', None) else None,
            status=str(getattr(contract, 'status', '')) if getattr(contract, 'status', None) else None,
            tradable=getattr(contract, 'tradable', None),
            expiration_date=str(getattr(contract, 'expiration_date', '')) if getattr(contract, 'expiration_date', None) else None,
            root_symbol=str(getattr(contract, 'root_symbol', '')) if getattr(contract, 'root_symbol', None) else None,
            underlying_asset_id=str(getattr(contract, 'underlying_asset_id', '')) if getattr(contract, 'underlying_asset_id', None) else None,
            type=getattr(contract, 'type', None),
            style=getattr(contract, 'style', None),
            strike_price=str(getattr(contract, 'strike_price', '')) if getattr(contract, 'strike_price', None) else None,
            multiplier=str(getattr(contract, 'multiplier', '')) if getattr(contract, 'multiplier', None) else None,
            size=str(getattr(contract, 'size', '')) if getattr(contract, 'size', None) else None,
            open_interest=getattr(contract, 'open_interest', None),
            open_interest_date=str(getattr(contract, 'open_interest_date', '')) if getattr(contract, 'open_interest_date', None) else None,
            close_price=str(getattr(contract, 'close_price', '')) if getattr(contract, 'close_price', None) else None,
            close_price_date=str(getattr(contract, 'close_price_date', '')) if getattr(contract, 'close_price_date', None) else None,
        )
    elif isinstance(contract, dict):
        return OptionContract(
            symbol=str(contract.get('symbol', '')),
            underlying_symbol=str(contract.get('underlying_symbol', '')),
            name=str(contract.get('name', '')) if contract.get('name') else None,
            status=str(contract.get('status', '')) if contract.get('status') else None,
            tradable=contract.get('tradable'),
            expiration_date=str(contract.get('expiration_date', '')) if contract.get('expiration_date') else None,
            root_symbol=str(contract.get('root_symbol', '')) if contract.get('root_symbol') else None,
            underlying_asset_id=str(contract.get('underlying_asset_id', '')) if contract.get('underlying_asset_id') else None,
            type=contract.get('type'),
            style=contract.get('style'),
            strike_price=str(contract.get('strike_price', '')) if contract.get('strike_price') else None,
            multiplier=str(contract.get('multiplier', '')) if contract.get('multiplier') else None,
            size=str(contract.get('size', '')) if contract.get('size') else None,
            open_interest=contract.get('open_interest'),
            open_interest_date=str(contract.get('open_interest_date', '')) if contract.get('open_interest_date') else None,
            close_price=str(contract.get('close_price', '')) if contract.get('close_price') else None,
            close_price_date=str(contract.get('close_price_date', '')) if contract.get('close_price_date') else None,
        )
    return None


class AlpacaMCPServer:
    """MCP Server for Alpaca trading and market data."""

    def __init__(self):
        """Initialize the Alpaca MCP server."""
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        self.paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"

        if not self.api_key or not self.secret_key:
            raise ValueError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set")

        # Initialize clients
        self.trading_client = TradingClient(
            self.api_key, self.secret_key, paper=self.paper
        )
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)

        # Determine host from MCP_HOST env variable, default to "0.0.0.0"
        mcp_host = os.getenv("MCP_HOST", "0.0.0.0")

        # Initialize MCP server
        self.app = FastMCP(
            "alpaca-trading",
            debug=True,
            json_response=True,
            host=mcp_host,
            port=8001,
            log_level="DEBUG"
        )
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tools."""

        @self.app.tool()
        async def get_account_info() -> AccountResponse:
            """Get account information and buying power."""
            try:
                logger.info("Getting account info")
                account = self.trading_client.get_account()

                account_info = AccountInfo(
                    account_id=str(account.id),
                    cash=float(account.cash),
                    buying_power=float(account.buying_power),
                    portfolio_value=float(account.portfolio_value),
                    equity=float(account.equity),
                    long_market_value=float(account.long_market_value or 0),
                    short_market_value=float(account.short_market_value or 0),
                    initial_margin=float(account.initial_margin or 0),
                    maintenance_margin=float(account.maintenance_margin or 0),
                    last_equity=float(account.last_equity),
                    daytrade_count=account.daytrade_count or 0,
                )

                return AccountResponse(success=True, data=account_info)
            except Exception as e:
                logger.error(f"Failed to get account info: {e}")
                return AccountResponse(success=False, error=str(e))

        @self.app.tool()
        async def get_positions() -> PositionsResponse:
            """Get current stock positions."""
            try:
                logger.info("Getting positions")
                positions = self.trading_client.get_all_positions()

                position_data = []
                for pos in positions:
                    position = Position(
                        symbol=pos.symbol,
                        quantity=float(pos.qty),
                        side=pos.side.value,
                        market_value=float(pos.market_value),
                        cost_basis=float(pos.cost_basis),
                        unrealized_pl=float(pos.unrealized_pl),
                        unrealized_plpc=float(pos.unrealized_plpc),
                        current_price=float(pos.current_price),
                        qty_available=(
                            float(pos.qty_available) if pos.qty_available else None
                        ),
                    )
                    position_data.append(position)

                logger.info(f"Retrieved {len(position_data)} positions")
                return PositionsResponse(success=True, data=position_data)
            except Exception as e:
                return PositionsResponse(success=False, error=str(e))

        @self.app.tool()
        async def get_orders(
            status: Optional[str] = None,
            limit: int = 100,
            symbols: Optional[str] = None,
        ) -> OrdersResponse:
            """Get order history with optional filtering.

            Args:
                status: Filter by order status (open, closed, all)
                limit: Maximum number of orders to return
                symbols: Comma-separated list of symbols to filter by
            """
            try:
                # Parse symbols if provided
                symbol_list = symbols.split(",") if symbols else None

                request = GetOrdersRequest(
                    status=status, limit=limit, symbols=symbol_list
                )

                orders = self.trading_client.get_orders(request)

                order_data = []
                for order in orders:
                    order_obj = Order(
                        id=str(order.id),  # Convert UUID to string
                        symbol=order.symbol,
                        qty=float(order.qty),
                        side=order.side.value if hasattr(order.side, 'value') else order.side,
                        order_type=order.order_type.value if hasattr(order.order_type, 'value') else order.order_type,
                        status=order.status.value if hasattr(order.status, 'value') else order.status,
                        submitted_at=order.submitted_at,
                        filled_at=order.filled_at,
                        filled_qty=(
                            float(order.filled_qty) if order.filled_qty else None
                        ),
                        filled_avg_price=(
                            float(order.filled_avg_price)
                            if order.filled_avg_price
                            else None
                        ),
                        limit_price=(
                            float(order.limit_price) if order.limit_price else None
                        ),
                        stop_price=(
                            float(order.stop_price) if order.stop_price else None
                        ),
                    )
                    order_data.append(order_obj)

                return OrdersResponse(success=True, data=order_data)
            except Exception as e:
                logger.error(f"Failed to get orders: {e}")
                return OrdersResponse(success=False, error=str(e))

        @self.app.tool()
        async def get_order(order_id: str) -> OrderResponse:
            """Get a specific order by ID.

            Args:
                order_id: ID of the order to retrieve
            """
            try:
                logger.info(f"Getting order: {order_id}")
                order = self.trading_client.get_order_by_id(order_id)

                order_obj = Order(
                    id=str(order.id),
                    symbol=order.symbol,
                    qty=float(order.qty),
                    side=order.side.value if hasattr(order.side, 'value') else order.side,
                    order_type=order.order_type.value if hasattr(order.order_type, 'value') else order.order_type,
                    status=order.status.value if hasattr(order.status, 'value') else order.status,
                    submitted_at=order.submitted_at,
                    filled_at=order.filled_at,
                    filled_qty=float(order.filled_qty) if order.filled_qty else None,
                    filled_avg_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                    limit_price=float(order.limit_price) if order.limit_price else None,
                    stop_price=float(order.stop_price) if order.stop_price else None,
                )

                return OrderResponse(success=True, data=order_obj)
            except Exception as e:
                logger.error(f"Failed to get order {order_id}: {e}")
                return OrderResponse(success=False, error=f"Order not found or error: {str(e)}")

        @self.app.tool()
        async def place_market_order(
            symbol: str, qty: float, side: str, time_in_force: str = "gtc"
        ) -> MCPResponse:
            """Place a market order.

            Args:
                symbol: Stock symbol to trade
                qty: Quantity of shares (must be > 0)
                side: 'buy' or 'sell'
                time_in_force: Time in force (gtc, day, ioc, fok)
            """
            # Validate inputs
            if error := validate_order_params(qty=qty):
                return MCPResponse(success=False, error=error)

            try:
                logger.info(f"Placing market order: {side} {qty} {symbol}")
                order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
                tif = TIME_IN_FORCE_MAP.get(time_in_force.lower(), TimeInForce.GTC)

                market_order_data = MarketOrderRequest(
                    symbol=symbol, qty=qty, side=order_side, time_in_force=tif
                )

                order = self.trading_client.submit_order(order_data=market_order_data)
                logger.info(f"Market order placed: {order.id}")

                return MCPResponse(
                    success=True,
                    data={
                        "order_id": str(order.id),
                        "symbol": order.symbol,
                        "qty": float(order.qty),
                        "side": order.side.value,
                        "status": order.status.value,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to place market order: {e}")
                return MCPResponse(success=False, error=str(e))

        @self.app.tool()
        async def place_limit_order(
            symbol: str,
            qty: float,
            side: str,
            limit_price: float,
            time_in_force: str = "gtc",
        ) -> MCPResponse:
            """Place a limit order.

            Args:
                symbol: Stock symbol to trade
                qty: Quantity of shares (must be > 0)
                side: 'buy' or 'sell'
                limit_price: Limit price for the order (must be > 0)
                time_in_force: Time in force (gtc, day, ioc, fok)
            """
            # Validate inputs
            if error := validate_order_params(qty=qty, limit_price=limit_price):
                return MCPResponse(success=False, error=error)

            try:
                logger.info(f"Placing limit order: {side} {qty} {symbol} @ {limit_price}")
                order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
                tif = TIME_IN_FORCE_MAP.get(time_in_force.lower(), TimeInForce.GTC)

                limit_order_data = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    limit_price=limit_price,
                    time_in_force=tif,
                )

                order = self.trading_client.submit_order(order_data=limit_order_data)
                logger.info(f"Limit order placed: {order.id}")

                return MCPResponse(
                    success=True,
                    data={
                        "order_id": str(order.id),
                        "symbol": order.symbol,
                        "qty": float(order.qty),
                        "side": order.side.value,
                        "limit_price": float(order.limit_price),
                        "status": order.status.value,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to place limit order: {e}")
                return MCPResponse(success=False, error=str(e))

        @self.app.tool()
        async def place_stop_order(
            symbol: str,
            qty: float,
            side: str,
            stop_price: float,
            time_in_force: str = "gtc",
        ) -> MCPResponse:
            """Place a stop order. Triggers a market order when stop price is reached.

            A stop order becomes a market order when stop_price is reached, guaranteeing
            execution but not the price. This is ONE order that activates at a trigger price.

            How it works:
            1. Order is inactive until market reaches stop_price
            2. Once triggered, immediately becomes a market order
            3. Fills at best available price (may be different from stop_price in fast markets)

            Example - SELL stop (stop-loss for long position):
                Current: Own 100 shares at $175
                stop_price: $170 (triggers when price drops to $170)
                Result: Market sell at whatever price is available (could be $170, $169.50, etc.)
                Use case: Exit position to limit loss, guaranteed fill

            Example - BUY stop (enter on breakout):
                Current price: $175
                stop_price: $180 (triggers when price rises to $180)
                Result: Market buy at whatever price is available
                Use case: Enter position on breakout, price doesn't matter

            Stop order vs Stop-limit order:
            - Stop order: Guarantees execution, price may slip
            - Stop-limit order: Guarantees max price, may not fill

            For protective strategies with BOTH stop-loss AND take-profit:
            - Entering NEW position: Use place_bracket_order
            - Protecting EXISTING position: Use place_oco_order

            Args:
                symbol: Stock symbol to trade
                qty: Quantity of shares (must be > 0)
                side: 'buy' or 'sell'
                stop_price: Price that triggers the market order (must be > 0)
                time_in_force: Time in force (gtc, day, ioc, fok)
            """
            # Validate inputs
            if error := validate_order_params(qty=qty, stop_price=stop_price):
                return MCPResponse(success=False, error=error)

            try:
                logger.info(f"Placing stop order: {side} {qty} {symbol} stop @ {stop_price}")
                order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
                tif = TIME_IN_FORCE_MAP.get(time_in_force.lower(), TimeInForce.GTC)

                stop_order_data = StopOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    stop_price=stop_price,
                    time_in_force=tif,
                )

                order = self.trading_client.submit_order(order_data=stop_order_data)
                logger.info(f"Stop order placed: {order.id}")

                return MCPResponse(
                    success=True,
                    data={
                        "order_id": str(order.id),
                        "symbol": order.symbol,
                        "qty": float(order.qty),
                        "side": order.side.value,
                        "stop_price": float(order.stop_price),
                        "status": order.status.value,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to place stop order: {e}")
                return MCPResponse(success=False, error=str(e))

        @self.app.tool()
        async def place_stop_limit_order(
            symbol: str,
            qty: float,
            side: str,
            stop_price: float,
            limit_price: float,
            time_in_force: str = "gtc",
        ) -> MCPResponse:
            """Place a stop-limit order (single order with two price components).

            A stop-limit order becomes active when the stop_price is reached, then executes
            as a limit order at the limit_price. This is ONE order, not two separate orders.

            How it works:
            1. Order is inactive until market reaches stop_price
            2. Once triggered, it becomes a limit order at limit_price
            3. Order fills at limit_price or better (or not at all if price moves away)

            Example - SELL stop-limit (protect downside):
                Current price: $175
                stop_price: $170 (triggers when price drops to $170)
                limit_price: $169 (sell at $169 or better, i.e., $169 or higher)
                Use case: Exit position if price drops, but don't sell below $169

            Example - BUY stop-limit (enter on breakout):
                Current price: $175
                stop_price: $180 (triggers when price rises to $180)
                limit_price: $181 (buy at $181 or better, i.e., $181 or lower)
                Use case: Enter position on breakout, but don't chase above $181

            IMPORTANT - For protective strategies with both stop-loss AND take-profit:
            - Entering NEW position: Use place_bracket_order (creates entry + 2 protective exits)
            - Protecting EXISTING position: Use place_oco_order (creates 2 protective exits only)
            Stop-limit orders are single directional - they only protect one side.

            Args:
                symbol: Stock symbol to trade
                qty: Quantity of shares (must be > 0)
                side: 'buy' or 'sell'
                stop_price: Price that triggers the order to become active (must be > 0)
                limit_price: Execution price once triggered - order fills at this price or better (must be > 0)
                time_in_force: Time in force (gtc, day, ioc, fok)
            """
            # Validate inputs
            if error := validate_order_params(qty=qty, stop_price=stop_price, limit_price=limit_price):
                return MCPResponse(success=False, error=error)

            try:
                logger.info(f"Placing stop-limit order: {side} {qty} {symbol} stop @ {stop_price} limit @ {limit_price}")
                order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
                tif = TIME_IN_FORCE_MAP.get(time_in_force.lower(), TimeInForce.GTC)

                stop_limit_order_data = StopLimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    stop_price=stop_price,
                    limit_price=limit_price,
                    time_in_force=tif,
                )

                order = self.trading_client.submit_order(order_data=stop_limit_order_data)
                logger.info(f"Stop-limit order placed: {order.id}")

                return MCPResponse(
                    success=True,
                    data={
                        "order_id": str(order.id),
                        "symbol": order.symbol,
                        "qty": float(order.qty),
                        "side": order.side.value,
                        "stop_price": float(order.stop_price),
                        "limit_price": float(order.limit_price),
                        "status": order.status.value,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to place stop-limit order: {e}")
                return MCPResponse(success=False, error=str(e))

        @self.app.tool()
        async def place_trailing_stop_order(
            symbol: str,
            qty: float,
            side: str,
            trail_percent: Optional[float] = None,
            trail_price: Optional[float] = None,
            time_in_force: str = "gtc",
        ) -> MCPResponse:
            """Place a trailing stop order. Stop price adjusts with market movement.

            Args:
                symbol: Stock symbol to trade
                qty: Quantity of shares (must be > 0)
                side: 'buy' or 'sell'
                trail_percent: Trail by percentage (e.g., 1.0 for 1%). Mutually exclusive with trail_price.
                trail_price: Trail by fixed dollar amount (must be > 0). Mutually exclusive with trail_percent.
                time_in_force: Time in force (gtc, day, ioc, fok)
            """
            # Validate inputs
            if error := validate_order_params(qty=qty, trail_price=trail_price):
                return MCPResponse(success=False, error=error)
            if trail_percent is not None and trail_percent <= 0:
                return MCPResponse(success=False, error="Trail percent must be greater than 0")

            if trail_percent is None and trail_price is None:
                return MCPResponse(
                    success=False,
                    error="Either trail_percent or trail_price must be provided"
                )
            if trail_percent is not None and trail_price is not None:
                return MCPResponse(
                    success=False,
                    error="Only one of trail_percent or trail_price can be provided, not both"
                )

            try:
                trail_desc = f"{trail_percent}%" if trail_percent else f"${trail_price}"
                logger.info(f"Placing trailing stop order: {side} {qty} {symbol} trail {trail_desc}")
                order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
                tif = TIME_IN_FORCE_MAP.get(time_in_force.lower(), TimeInForce.GTC)

                trailing_stop_data = TrailingStopOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    trail_percent=trail_percent,
                    trail_price=trail_price,
                    time_in_force=tif,
                )

                order = self.trading_client.submit_order(order_data=trailing_stop_data)
                logger.info(f"Trailing stop order placed: {order.id}")

                return MCPResponse(
                    success=True,
                    data={
                        "order_id": str(order.id),
                        "symbol": order.symbol,
                        "qty": float(order.qty),
                        "side": order.side.value,
                        "trail_percent": float(order.trail_percent) if order.trail_percent else None,
                        "trail_price": float(order.trail_price) if order.trail_price else None,
                        "status": order.status.value,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to place trailing stop order: {e}")
                return MCPResponse(success=False, error=str(e))

        @self.app.tool()
        async def place_bracket_order(
            symbol: str,
            qty: float,
            side: str,
            take_profit_limit_price: float,
            stop_loss_stop_price: float,
            stop_loss_limit_price: Optional[float] = None,
            entry_type: str = "market",
            entry_limit_price: Optional[float] = None,
            time_in_force: str = "gtc",
        ) -> MCPResponse:
            """Place a bracket order with entry, take profit, and stop loss (THREE orders).

            A bracket order is an advanced order type that automatically places THREE orders:
            1. Entry order (market or limit) - enters the position
            2. Take profit limit order - automatically placed when entry fills (upside protection)
            3. Stop loss order - automatically placed when entry fills (downside protection)

            The take profit and stop loss are OCO (one-cancels-other): when one fills, the other
            is automatically cancelled. This creates a "bracket" around your position.

            Example - BUY bracket with market entry:
                Entry: BUY 100 shares AAPL at market (assume fills at $175)
                Take profit: SELL 100 shares at $180 limit (exit with profit)
                Stop loss: SELL 100 shares at $170 stop (exit to limit loss)
                Result: Position protected on both sides - max gain $5/share, max loss $5/share

            Example - BUY bracket with limit entry and stop-limit protection:
                Entry: BUY 100 shares AAPL at $175 limit
                Take profit: SELL 100 shares at $185 limit
                Stop loss: SELL 100 shares at $170 stop, $169 limit (won't sell below $169)
                Result: Enter only at $175 or better, protected $169-$185 range

            Example - SELL (short) bracket:
                Entry: SELL 100 shares AAPL at $175 limit (short position)
                Take profit: BUY 100 shares at $165 limit (cover short with profit)
                Stop loss: BUY 100 shares at $180 stop (cover short to limit loss)
                Result: Profit if price drops to $165, exit if price rises to $180

            When to use bracket orders:
            - Entering new positions with defined risk/reward
            - Want automatic protection without monitoring
            - Trading with preset profit targets and stop losses
            - Swing trading or position trading

            When NOT to use bracket orders:
            - Already in a position (use place_oco_order instead for existing positions)
            - Want asymmetric risk/reward (different stop vs profit distances)
            - Need trailing stops (use place_trailing_stop_order)

            Args:
                symbol: Stock symbol to trade
                qty: Quantity of shares (must be > 0)
                side: 'buy' or 'sell' for the entry order
                take_profit_limit_price: Limit price for take profit exit (must be > 0)
                stop_loss_stop_price: Stop price that triggers stop loss exit (must be > 0)
                stop_loss_limit_price: Optional limit price for stop loss. If provided, creates a stop-limit order (won't exit below/above this price). If omitted, creates a stop market order (guarantees exit at any price).
                entry_type: 'market' (immediate entry) or 'limit' (entry at specific price)
                entry_limit_price: Required if entry_type is 'limit' (must be > 0)
                time_in_force: Time in force (gtc, day)
            """
            # Validate inputs
            if error := validate_order_params(qty=qty, limit_price=entry_limit_price, stop_price=stop_loss_stop_price):
                return MCPResponse(success=False, error=error)
            if take_profit_limit_price <= 0:
                return MCPResponse(success=False, error="Take profit limit price must be greater than 0")
            if stop_loss_limit_price is not None and stop_loss_limit_price <= 0:
                return MCPResponse(success=False, error="Stop loss limit price must be greater than 0")

            if entry_type.lower() == "limit" and entry_limit_price is None:
                return MCPResponse(
                    success=False,
                    error="entry_limit_price is required when entry_type is 'limit'"
                )

            try:
                from alpaca.trading.enums import OrderClass

                logger.info(f"Placing bracket order: {side} {qty} {symbol} TP @ {take_profit_limit_price} SL @ {stop_loss_stop_price}")
                order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
                tif = TIME_IN_FORCE_MAP.get(time_in_force.lower(), TimeInForce.GTC)

                # Build the bracket order
                if entry_type.lower() == "market":
                    order_data = MarketOrderRequest(
                        symbol=symbol,
                        qty=qty,
                        side=order_side,
                        time_in_force=tif,
                        order_class=OrderClass.BRACKET,
                        take_profit={"limit_price": take_profit_limit_price},
                        stop_loss={
                            "stop_price": stop_loss_stop_price,
                            **({"limit_price": stop_loss_limit_price} if stop_loss_limit_price else {})
                        },
                    )
                else:
                    order_data = LimitOrderRequest(
                        symbol=symbol,
                        qty=qty,
                        side=order_side,
                        limit_price=entry_limit_price,
                        time_in_force=tif,
                        order_class=OrderClass.BRACKET,
                        take_profit={"limit_price": take_profit_limit_price},
                        stop_loss={
                            "stop_price": stop_loss_stop_price,
                            **({"limit_price": stop_loss_limit_price} if stop_loss_limit_price else {})
                        },
                    )

                order = self.trading_client.submit_order(order_data=order_data)
                logger.info(f"Bracket order placed: {order.id}")

                return MCPResponse(
                    success=True,
                    data={
                        "order_id": str(order.id),
                        "symbol": order.symbol,
                        "qty": float(order.qty),
                        "side": order.side.value,
                        "entry_type": entry_type,
                        "entry_limit_price": entry_limit_price,
                        "take_profit_limit_price": take_profit_limit_price,
                        "stop_loss_stop_price": stop_loss_stop_price,
                        "stop_loss_limit_price": stop_loss_limit_price,
                        "status": order.status.value,
                        "order_class": "bracket",
                    },
                )
            except Exception as e:
                logger.error(f"Failed to place bracket order: {e}")
                return MCPResponse(success=False, error=str(e))

        @self.app.tool()
        async def place_oco_order(
            symbol: str,
            qty: float,
            side: str,
            take_profit_limit_price: float,
            stop_loss_stop_price: float,
            stop_loss_limit_price: Optional[float] = None,
            time_in_force: str = "gtc",
        ) -> MCPResponse:
            """Place an OCO (One-Cancels-Other) order to protect an EXISTING position (TWO orders).

            OCO places TWO linked orders - when one fills, the other automatically cancels:
            1. Take profit limit order - exit with profit
            2. Stop loss order - exit to limit loss

            Use this ONLY for positions you already own. For entering new positions with
            protection, use place_bracket_order instead.

            Example - Protect existing LONG position:
                Current: Own 100 shares AAPL, purchased at $175, now trading at $178
                Take profit: SELL 100 shares at $185 limit (exit with $10/share profit)
                Stop loss: SELL 100 shares at $170 stop (exit with $5/share loss)
                Result: Exit at $185 if price rises, or $170 if price falls

            Example - Protect existing LONG with stop-limit protection:
                Current: Own 100 shares AAPL at $175
                Take profit: SELL 100 shares at $185 limit
                Stop loss: SELL 100 shares at $170 stop, $169 limit
                Result: Won't sell below $169 even if stop triggers (may not exit in crash)

            Example - Protect existing SHORT position:
                Current: Short 100 shares AAPL at $175, now trading at $172
                Take profit: BUY 100 shares at $165 limit (cover with $10/share profit)
                Stop loss: BUY 100 shares at $180 stop (cover with $5/share loss)
                Result: Cover at $165 if price drops, or $180 if price rises

            When to use OCO:
            - Already holding a position (long or short)
            - Want to add protection to unprotected position
            - Adjusting existing stop/profit levels

            When NOT to use OCO:
            - Entering a new position (use place_bracket_order instead)
            - Want multiple exit levels (OCO exits full quantity on first fill)

            Args:
                symbol: Stock symbol (must have existing position)
                qty: Quantity of shares to exit (must be > 0, should not exceed position size)
                side: 'sell' (for long positions) or 'buy' (for short positions)
                take_profit_limit_price: Limit price to exit with profit (must be > 0)
                stop_loss_stop_price: Stop price that triggers stop loss exit (must be > 0)
                stop_loss_limit_price: Optional limit price for stop loss. If provided, won't exit below/above this price (creates stop-limit). If omitted, guarantees exit at any price (stop market).
                time_in_force: Time in force (gtc, day)
            """
            # Validate inputs
            if error := validate_order_params(qty=qty, stop_price=stop_loss_stop_price):
                return MCPResponse(success=False, error=error)
            if take_profit_limit_price <= 0:
                return MCPResponse(success=False, error="Take profit limit price must be greater than 0")
            if stop_loss_limit_price is not None and stop_loss_limit_price <= 0:
                return MCPResponse(success=False, error="Stop loss limit price must be greater than 0")

            try:
                from alpaca.trading.enums import OrderClass

                logger.info(f"Placing OCO order: {side} {qty} {symbol} TP @ {take_profit_limit_price} SL @ {stop_loss_stop_price}")
                order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
                tif = TIME_IN_FORCE_MAP.get(time_in_force.lower(), TimeInForce.GTC)

                # OCO orders require both the nested take_profit parameter AND
                # the main limit_price (for compatibility with older SDK versions)
                order_data = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    limit_price=take_profit_limit_price,  # Required for older alpaca-py versions
                    time_in_force=tif,
                    order_class=OrderClass.OCO,
                    take_profit={"limit_price": take_profit_limit_price},  # Required by Alpaca API
                    stop_loss={
                        "stop_price": stop_loss_stop_price,
                        **({"limit_price": stop_loss_limit_price} if stop_loss_limit_price else {})
                    },
                )

                order = self.trading_client.submit_order(order_data=order_data)
                logger.info(f"OCO order placed: {order.id}")

                return MCPResponse(
                    success=True,
                    data={
                        "order_id": str(order.id),
                        "symbol": order.symbol,
                        "qty": float(order.qty),
                        "side": order.side.value,
                        "take_profit_limit_price": take_profit_limit_price,
                        "stop_loss_stop_price": stop_loss_stop_price,
                        "stop_loss_limit_price": stop_loss_limit_price,
                        "status": order.status.value,
                        "order_class": "oco",
                    },
                )
            except Exception as e:
                logger.error(f"Failed to place OCO order: {e}")
                return MCPResponse(success=False, error=str(e))

        @self.app.tool()
        async def cancel_order(order_id: str) -> MCPResponse:
            """Cancel a pending order.

            Args:
                order_id: ID of the order to cancel
            """
            try:
                logger.info(f"Cancelling order: {order_id}")
                self.trading_client.cancel_order_by_id(order_id)
                logger.info(f"Order cancelled: {order_id}")
                return MCPResponse(
                    success=True,
                    data={"message": f"Order {order_id} cancelled successfully"},
                )
            except Exception as e:
                logger.error(f"Failed to cancel order {order_id}: {e}")
                return MCPResponse(success=False, error=str(e))

        @self.app.tool()
        async def close_position(
            symbol: str,
            qty: Optional[float] = None,
            percentage: Optional[float] = None,
        ) -> MCPResponse:
            """Close all or part of a position.

            Args:
                symbol: Stock symbol to close
                qty: Quantity to close. If not provided, closes entire position.
                percentage: Percentage of position to close (0-100). Mutually exclusive with qty.
            """
            if qty is not None and percentage is not None:
                return MCPResponse(
                    success=False,
                    error="Only one of qty or percentage can be provided, not both"
                )
            if qty is not None and qty <= 0:
                return MCPResponse(success=False, error="Quantity must be greater than 0")
            if percentage is not None and (percentage <= 0 or percentage > 100):
                return MCPResponse(success=False, error="Percentage must be between 0 and 100")

            try:
                logger.info(f"Closing position: {symbol} qty={qty} percentage={percentage}")

                # Build close position parameters
                close_options = {}
                if qty is not None:
                    close_options["qty"] = str(qty)
                elif percentage is not None:
                    close_options["percentage"] = str(percentage)

                result = self.trading_client.close_position(symbol, close_options=close_options if close_options else None)
                logger.info(f"Position closed: {symbol}")

                return MCPResponse(
                    success=True,
                    data={
                        "order_id": str(result.id),
                        "symbol": result.symbol,
                        "qty": float(result.qty),
                        "side": result.side.value,
                        "status": result.status.value,
                        "message": f"Position close order submitted for {symbol}",
                    },
                )
            except Exception as e:
                logger.error(f"Failed to close position {symbol}: {e}")
                return MCPResponse(success=False, error=f"Failed to close position: {str(e)}")

        @self.app.tool()
        async def close_all_positions(cancel_orders: bool = False) -> MCPResponse:
            """Close all open positions.

            Args:
                cancel_orders: If True, also cancels all open orders before closing positions.
            """
            try:
                logger.info(f"Closing all positions (cancel_orders={cancel_orders})")

                results = self.trading_client.close_all_positions(cancel_orders=cancel_orders)
                logger.info(f"Close all positions completed: {len(results)} positions")

                closed_positions = []
                failed_positions = []

                for result in results:
                    if hasattr(result, 'body') and hasattr(result.body, 'symbol'):
                        # Successful close
                        closed_positions.append({
                            "symbol": result.body.symbol,
                            "order_id": str(result.body.id),
                        })
                    elif hasattr(result, 'symbol'):
                        closed_positions.append({
                            "symbol": result.symbol,
                            "order_id": str(result.id),
                        })
                    else:
                        failed_positions.append(str(result))

                return MCPResponse(
                    success=True,
                    data={
                        "closed_count": len(closed_positions),
                        "failed_count": len(failed_positions),
                        "closed_positions": closed_positions,
                        "failed_positions": failed_positions,
                        "message": f"Closed {len(closed_positions)} positions" + (f", {len(failed_positions)} failed" if failed_positions else ""),
                    },
                )
            except Exception as e:
                logger.error(f"Failed to close all positions: {e}")
                return MCPResponse(success=False, error=f"Failed to close all positions: {str(e)}")

        @self.app.tool()
        async def get_latest_quotes(symbols: str) -> QuotesResponse:
            """Get real-time stock quotes.

            Args:
                symbols: Comma-separated list of stock symbols
            """
            try:
                symbol_list = [s.strip().upper() for s in symbols.split(",")]

                request = StockLatestQuoteRequest(symbol_or_symbols=symbol_list)
                quotes = self.data_client.get_stock_latest_quote(request)

                quote_data = []
                for symbol, quote in quotes.items():
                    quote_obj = QuoteData(
                        symbol=symbol,
                        bid_price=float(quote.bid_price) if quote.bid_price else None,
                        ask_price=float(quote.ask_price) if quote.ask_price else None,
                        bid_size=int(quote.bid_size) if quote.bid_size else None,
                        ask_size=int(quote.ask_size) if quote.ask_size else None,
                        timestamp=quote.timestamp,
                    )
                    quote_data.append(quote_obj)

                return QuotesResponse(success=True, data=quote_data)
            except Exception as e:
                return QuotesResponse(success=False, error=str(e))

        @self.app.tool()
        async def get_stock_bars(
            symbols: str,
            timeframe: str = "1Day",
            start: Optional[str] = None,
            end: Optional[str] = None,
            limit: int = 100,
        ) -> BarsResponse:
            """Get historical price data (OHLCV).

            Args:
                symbols: Comma-separated list of stock symbols
                timeframe: Time frame (1Min, 5Min, 15Min, 30Min, 1Hour, 1Day, 1Week, 1Month)
                start: Start date (YYYY-MM-DD format)
                end: End date (YYYY-MM-DD format)
                limit: Maximum number of bars to return
            """
            try:
                symbol_list = [s.strip().upper() for s in symbols.split(",")]

                # Convert timeframe string to Alpaca TimeFrame
                timeframe_map = {
                    "1Min": TimeFrame.Minute,
                    "5Min": TimeFrame(5, "Min"),
                    "15Min": TimeFrame(15, "Min"),
                    "30Min": TimeFrame(30, "Min"),
                    "1Hour": TimeFrame.Hour,
                    "1Day": TimeFrame.Day,
                    "1Week": TimeFrame.Week,
                    "1Month": TimeFrame.Month,
                }

                tf = timeframe_map.get(timeframe, TimeFrame.Day)

                # Parse dates if provided
                start_date = datetime.fromisoformat(start) if start else None
                end_date = datetime.fromisoformat(end) if end else None

                request = StockBarsRequest(
                    symbol_or_symbols=symbol_list,
                    timeframe=tf,
                    start=start_date,
                    end=end_date,
                    limit=limit,
                )

                bars = self.data_client.get_stock_bars(request)

                bar_data = []
                # BarSet has a .data attribute that's a dict of symbol -> list of bars
                # Iterate through actual data returned by API rather than input symbols
                for symbol, symbol_bars in bars.data.items():
                    for bar in symbol_bars:
                        bar_obj = BarData(
                            symbol=symbol,
                            timestamp=bar.timestamp,
                            open=float(bar.open),
                            high=float(bar.high),
                            low=float(bar.low),
                            close=float(bar.close),
                            volume=int(bar.volume),
                            trade_count=(
                                int(bar.trade_count) if bar.trade_count else None
                            ),
                            vwap=float(bar.vwap) if bar.vwap else None,
                        )
                        bar_data.append(bar_obj)

                return BarsResponse(success=True, data=bar_data)
            except Exception as e:
                return BarsResponse(success=False, error=str(e))

        @self.app.tool()
        async def get_portfolio_history(
            period: str = "1M", timeframe: str = "1D", extended_hours: bool = False
        ) -> MCPResponse:
            """Get portfolio performance over time.

            Args:
                period: Time period (1D, 7D, 1M, 3M, 1Y, 2Y, 5Y, max)
                timeframe: Data frequency (1Min, 5Min, 15Min, 1H, 1D)
                extended_hours: Include extended hours data
            """
            try:
                request = GetPortfolioHistoryRequest(
                    period=period, timeframe=timeframe, extended_hours=extended_hours
                )

                history = self.trading_client.get_portfolio_history(request)

                # Convert to list of dictionaries for JSON serialization
                portfolio_data = []
                for i, timestamp in enumerate(history.timestamp):
                    portfolio_data.append(
                        {
                            "timestamp": timestamp,
                            "equity": (
                                float(history.equity[i])
                                if i < len(history.equity)
                                else None
                            ),
                            "profit_loss": (
                                float(history.profit_loss[i])
                                if i < len(history.profit_loss)
                                else None
                            ),
                            "profit_loss_pct": (
                                float(history.profit_loss_pct[i])
                                if i < len(history.profit_loss_pct)
                                else None
                            ),
                        }
                    )

                return MCPResponse(success=True, data=portfolio_data)
            except Exception as e:
                return MCPResponse(success=False, error=str(e))

        @self.app.tool()
        async def get_option_contracts(
            underlying_symbols: Optional[str] = None,
            expiration_date: Optional[str] = None,
            expiration_date_gte: Optional[str] = None,
            expiration_date_lte: Optional[str] = None,
            root_symbol: Optional[str] = None,
            contract_type: Optional[str] = None,
            style: Optional[str] = None,
            strike_price_gte: Optional[str] = None,
            strike_price_lte: Optional[str] = None,
            limit: int = 100,
        ) -> OptionContractsResponse:
            """Get option contracts with filtering criteria.

            Args:
                underlying_symbols: Comma-separated list of underlying symbols (e.g., "AAPL,SPY")
                expiration_date: Specific expiration date (YYYY-MM-DD)
                expiration_date_gte: Expiration date greater than or equal to (YYYY-MM-DD)
                expiration_date_lte: Expiration date less than or equal to (YYYY-MM-DD)
                root_symbol: Option root symbol
                contract_type: Contract type ('call' or 'put')
                style: Exercise style ('american' or 'european')
                strike_price_gte: Strike price greater than or equal to
                strike_price_lte: Strike price less than or equal to
                limit: Maximum number of contracts to return (default: 100, max: 10000)
            """
            try:
                # Parse underlying symbols
                symbol_list = None
                if underlying_symbols:
                    symbol_list = [s.strip().upper() for s in underlying_symbols.split(",")]

                # Build request with minimal parameters for broader search
                request_params = {"limit": min(limit, 1000)}  # Cap at 1000
                if symbol_list:
                    request_params["underlying_symbols"] = symbol_list
                if expiration_date:
                    request_params["expiration_date"] = expiration_date
                if expiration_date_gte:
                    request_params["expiration_date_gte"] = expiration_date_gte
                if expiration_date_lte:
                    request_params["expiration_date_lte"] = expiration_date_lte
                if root_symbol:
                    request_params["root_symbol"] = root_symbol
                if contract_type:
                    # Map contract type to Alpaca enum
                    contract_type_map = {
                        "call": AlpacaContractType.CALL,
                        "put": AlpacaContractType.PUT,
                    }
                    request_params["type"] = contract_type_map.get(contract_type.lower())
                if style:
                    # Map exercise style to Alpaca enum
                    style_map = {
                        "american": AlpacaExerciseStyle.AMERICAN,
                        "european": AlpacaExerciseStyle.EUROPEAN,
                    }
                    request_params["style"] = style_map.get(style.lower())
                if strike_price_gte:
                    request_params["strike_price_gte"] = strike_price_gte
                if strike_price_lte:
                    request_params["strike_price_lte"] = strike_price_lte

                request = GetOptionContractsRequest(**request_params)
                response = self.trading_client.get_option_contracts(request)

                # Handle OptionContractsResponse object
                if hasattr(response, 'option_contracts'):
                    # Response is an OptionContractsResponse object
                    contracts = response.option_contracts
                elif isinstance(response, tuple):
                    # Response is a tuple
                    contracts = response[0] if response else []
                elif isinstance(response, list):
                    # Response is already a list
                    contracts = response
                else:
                    # Unknown structure, try to iterate
                    contracts = []

                contract_data = []
                for contract in contracts:
                    option_contract = parse_option_contract(contract)
                    if option_contract:
                        contract_data.append(option_contract)

                return OptionContractsResponse(success=True, data=contract_data)
            except Exception as e:
                return OptionContractsResponse(success=False, error=str(e))

        @self.app.tool()
        async def get_option_contract(symbol: str) -> OptionContractsResponse:
            """Get a specific option contract by symbol.

            Args:
                symbol: Option contract symbol (e.g., "AAPL241220C00150000")
            """
            try:
                response = self.trading_client.get_option_contract(symbol)

                # Handle different response structures
                if hasattr(response, 'option_contracts'):
                    # Response is an OptionContractsResponse object
                    contracts = response.option_contracts
                    contract = contracts[0] if contracts else None
                elif isinstance(response, tuple):
                    contract = response[0] if response else None
                else:
                    contract = response
                
                if not contract:
                    return OptionContractsResponse(success=False, error=f"No contract found for {symbol}")

                option_contract = parse_option_contract(contract)
                if not option_contract:
                    return OptionContractsResponse(success=False, error="Unknown contract data structure")

                return OptionContractsResponse(success=True, data=[option_contract])
            except Exception as e:
                return OptionContractsResponse(success=False, error=str(e))

        @self.app.tool()
        async def get_option_positions() -> OptionPositionsResponse:
            """Get current option positions."""
            try:
                positions = self.trading_client.get_all_positions()

                option_position_data = []
                for pos in positions:
                    # Filter for option positions using asset_class
                    asset_class = getattr(pos, 'asset_class', None)
                    is_option = (
                        asset_class == 'us_option' or
                        (asset_class and 'option' in str(asset_class).lower())
                    )
                    if is_option:
                        # Parse option symbol for details (OCC format: SYMBOL + YYMMDD + C/P + strike*1000)
                        symbol = pos.symbol
                        contract_type = None
                        if len(symbol) >= 15:
                            type_char = symbol[-9:-8] if len(symbol) > 9 else ''
                            if type_char == 'C':
                                contract_type = ContractType.CALL
                            elif type_char == 'P':
                                contract_type = ContractType.PUT

                        option_position = OptionPosition(
                            symbol=symbol,
                            quantity=float(pos.qty),
                            side=pos.side.value if hasattr(pos.side, 'value') else pos.side,
                            market_value=float(pos.market_value),
                            cost_basis=float(pos.cost_basis),
                            unrealized_pl=float(pos.unrealized_pl),
                            unrealized_plpc=float(pos.unrealized_plpc),
                            current_price=float(pos.current_price) if pos.current_price else None,
                            contract_type=contract_type,
                            strike_price=None,
                            expiration_date=None,
                        )
                        option_position_data.append(option_position)

                return OptionPositionsResponse(success=True, data=option_position_data)
            except Exception as e:
                return OptionPositionsResponse(success=False, error=str(e))

        @self.app.tool()
        async def place_option_order(
            symbol: str,
            qty: float,
            side: str,
            position_intent: str,
            order_type: str = "market",
            limit_price: Optional[float] = None,
            time_in_force: str = "gtc",
        ) -> MCPResponse:
            """Place a single-leg option order.

            Args:
                symbol: Option contract symbol (e.g., "AAPL241220C00150000")
                qty: Quantity of contracts
                side: 'buy' or 'sell'
                position_intent: 'buy_to_open', 'buy_to_close', 'sell_to_open', 'sell_to_close'
                order_type: 'market' or 'limit'
                limit_price: Limit price (required for limit orders)
                time_in_force: Time in force (gtc, day, ioc, fok)
            """
            try:
                from alpaca.trading.enums import OrderClass

                order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
                tif = TIME_IN_FORCE_MAP.get(time_in_force.lower(), TimeInForce.GTC)
                intent = POSITION_INTENT_MAP.get(position_intent.lower())

                if intent is None:
                    return MCPResponse(
                        success=False,
                        error=f"Invalid position_intent: {position_intent}. Must be one of: buy_to_open, buy_to_close, sell_to_open, sell_to_close"
                    )

                # Create option leg
                option_leg = OptionLegRequest(
                    symbol=symbol,
                    ratio_qty=1.0,  # Single leg
                    side=order_side,
                    position_intent=intent,
                )

                # Build order request based on type
                if order_type.lower() == "market":
                    order_data = MarketOrderRequest(
                        symbol=symbol,  # For options, this is the option symbol
                        qty=qty,
                        side=order_side,
                        time_in_force=tif,
                        order_class=OrderClass.SIMPLE,
                        legs=[option_leg],
                    )
                elif order_type.lower() == "limit":
                    if limit_price is None:
                        return MCPResponse(success=False, error="Limit price required for limit orders")

                    order_data = LimitOrderRequest(
                        symbol=symbol,
                        qty=qty,
                        side=order_side,
                        limit_price=limit_price,
                        time_in_force=tif,
                        order_class=OrderClass.SIMPLE,
                        legs=[option_leg],
                    )
                else:
                    return MCPResponse(success=False, error=f"Unsupported order type: {order_type}")

                order = self.trading_client.submit_order(order_data=order_data)

                return MCPResponse(
                    success=True,
                    data={
                        "order_id": str(order.id),
                        "symbol": order.symbol,
                        "qty": float(order.qty),
                        "side": order.side.value if hasattr(order.side, 'value') else order.side,
                        "order_type": order.order_type.value if hasattr(order.order_type, 'value') else order.order_type,
                        "status": order.status.value if hasattr(order.status, 'value') else order.status,
                        "limit_price": float(order.limit_price) if order.limit_price else None,
                    },
                )
            except Exception as e:
                return MCPResponse(success=False, error=str(e))

        @self.app.tool()
        async def place_multi_leg_option_order(
            legs: List[Dict[str, Any]],
            order_type: str = "market",
            limit_price: Optional[float] = None,
            time_in_force: str = "gtc",
        ) -> MCPResponse:
            """Place a multi-leg option order (spreads, straddles, etc.).

            Args:
                legs: List of option legs, each containing:
                    - symbol: Option contract symbol
                    - ratio_qty: Ratio quantity for this leg
                    - side: 'buy' or 'sell'
                    - position_intent: 'buy_to_open', 'buy_to_close', 'sell_to_open', 'sell_to_close'
                order_type: 'market' or 'limit'
                limit_price: Net limit price for the strategy (required for limit orders)
                time_in_force: Time in force (gtc, day, ioc, fok)
            """
            try:
                from alpaca.trading.enums import OrderClass

                if not legs:
                    return MCPResponse(success=False, error="At least one leg is required")

                tif = TIME_IN_FORCE_MAP.get(time_in_force.lower(), TimeInForce.GTC)

                # Create option legs
                option_legs = []
                for i, leg in enumerate(legs):
                    order_side = OrderSide.BUY if leg["side"].lower() == "buy" else OrderSide.SELL
                    intent = POSITION_INTENT_MAP.get(leg.get("position_intent", "").lower())

                    if intent is None:
                        return MCPResponse(
                            success=False,
                            error=f"Invalid position_intent in leg {i}: {leg.get('position_intent')}. Must be one of: buy_to_open, buy_to_close, sell_to_open, sell_to_close"
                        )

                    option_leg = OptionLegRequest(
                        symbol=leg["symbol"],
                        ratio_qty=float(leg["ratio_qty"]),
                        side=order_side,
                        position_intent=intent,
                    )
                    option_legs.append(option_leg)

                # Use the first leg's symbol as the primary symbol
                primary_symbol = legs[0]["symbol"]

                # Calculate total quantity (use the first leg's ratio as base)
                total_qty = abs(legs[0]["ratio_qty"])

                # Build order request
                if order_type.lower() == "market":
                    order_data = MarketOrderRequest(
                        symbol=primary_symbol,
                        qty=total_qty,
                        side=OrderSide.BUY,  # Multi-leg orders use BUY side
                        time_in_force=tif,
                        order_class=OrderClass.MLEG,
                        legs=option_legs,
                    )
                elif order_type.lower() == "limit":
                    if limit_price is None:
                        return MCPResponse(success=False, error="Limit price required for limit orders")

                    order_data = LimitOrderRequest(
                        symbol=primary_symbol,
                        qty=total_qty,
                        side=OrderSide.BUY,
                        limit_price=limit_price,
                        time_in_force=tif,
                        order_class=OrderClass.MLEG,
                        legs=option_legs,
                    )
                else:
                    return MCPResponse(success=False, error=f"Unsupported order type: {order_type}")

                order = self.trading_client.submit_order(order_data=order_data)

                return MCPResponse(
                    success=True,
                    data={
                        "order_id": str(order.id),
                        "symbol": order.symbol,
                        "qty": float(order.qty),
                        "side": order.side.value if hasattr(order.side, 'value') else order.side,
                        "order_type": order.order_type.value if hasattr(order.order_type, 'value') else order.order_type,
                        "order_class": "multi_leg",
                        "status": order.status.value if hasattr(order.status, 'value') else order.status,
                        "limit_price": float(order.limit_price) if order.limit_price else None,
                        "legs": len(option_legs),
                    },
                )
            except Exception as e:
                return MCPResponse(success=False, error=str(e))

        @self.app.tool()
        async def exercise_option_position(
            symbol: str,
            qty: Optional[float] = None,
        ) -> MCPResponse:
            """Exercise an option position.

            Args:
                symbol: Option contract symbol to exercise
                qty: Quantity to exercise (if None, exercises all available)
            """
            try:
                # Get current position to validate
                positions = self.trading_client.get_all_positions()
                option_position = None
                
                for pos in positions:
                    if pos.symbol == symbol:
                        option_position = pos
                        break
                
                if not option_position:
                    return MCPResponse(success=False, error=f"No position found for {symbol}")

                # Use all available quantity if not specified
                exercise_qty = qty if qty is not None else float(option_position.qty)

                # Exercise the position
                result = self.trading_client.exercise_options_position(
                    symbol=symbol,
                    qty=exercise_qty
                )

                return MCPResponse(
                    success=True,
                    data={
                        "symbol": symbol,
                        "exercised_qty": exercise_qty,
                        "message": f"Successfully exercised {exercise_qty} contracts of {symbol}",
                    },
                )
            except Exception as e:
                return MCPResponse(success=False, error=str(e))

def main():
    """Main entry point for the Alpaca MCP server."""
    # MCP_TRANSPORT env var sets the transport type (stdio, sse, streamable-http)
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    # Command-line flags override the env var
    if "--sse" in sys.argv:
        transport = "sse"
    elif "--streamable-http" in sys.argv or "--streamable" in sys.argv:
        transport = "streamable-http"

    server = AlpacaMCPServer()
    server.app.run(transport=transport)

if __name__ == "__main__":
    main()
