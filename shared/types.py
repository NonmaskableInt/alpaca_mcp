"""Shared type definitions for MCP servers."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    """Order side enumeration."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enumeration."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeFrame(str, Enum):
    """Time frame enumeration."""

    MINUTE = "1Min"
    FIVE_MINUTES = "5Min"
    FIFTEEN_MINUTES = "15Min"
    THIRTY_MINUTES = "30Min"
    HOUR = "1Hour"
    DAILY = "1Day"
    WEEKLY = "1Week"
    MONTHLY = "1Month"


class TechnicalIndicator(str, Enum):
    """Technical indicator enumeration."""

    RSI = "RSI"
    MACD = "MACD"
    BOLLINGER_BANDS = "BBANDS"
    SMA = "SMA"
    EMA = "EMA"
    STOCHASTIC = "STOCH"
    ADX = "ADX"
    WILLIAMS_R = "WILLR"


class ContractType(str, Enum):
    """Option contract type enumeration."""
    
    CALL = "call"
    PUT = "put"


class ExerciseStyle(str, Enum):
    """Option exercise style enumeration."""
    
    AMERICAN = "american"
    EUROPEAN = "european"


class PositionIntent(str, Enum):
    """Position intent enumeration for options."""
    
    BUY_TO_OPEN = "buy_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_OPEN = "sell_to_open"
    SELL_TO_CLOSE = "sell_to_close"


# Base Models
class QuoteData(BaseModel):
    """Stock quote data."""

    symbol: str
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    last_price: Optional[float] = None
    timestamp: Optional[datetime] = None


class BarData(BaseModel):
    """Price bar data (OHLCV)."""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    trade_count: Optional[int] = None
    vwap: Optional[float] = None


class Position(BaseModel):
    """Stock position data."""

    symbol: str
    quantity: float
    side: str  # "long" or "short"
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_plpc: float
    current_price: float
    qty_available: Optional[float] = None


class Order(BaseModel):
    """Order data."""

    id: str
    symbol: str
    qty: float
    side: OrderSide
    order_type: OrderType
    status: str
    submitted_at: datetime
    filled_at: Optional[datetime] = None
    filled_qty: Optional[float] = None
    filled_avg_price: Optional[float] = None
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None


class AccountInfo(BaseModel):
    """Account information."""

    account_id: str
    cash: float
    buying_power: float
    portfolio_value: float
    equity: float
    long_market_value: float
    short_market_value: float
    initial_margin: float
    maintenance_margin: float
    last_equity: float
    daytrade_count: int


class CompanyOverview(BaseModel):
    """Company overview data."""

    symbol: str
    name: str
    description: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    book_value: Optional[float] = None
    dividend_per_share: Optional[float] = None
    dividend_yield: Optional[float] = None
    eps: Optional[float] = None
    revenue_per_share_ttm: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin_ttm: Optional[float] = None
    return_on_assets_ttm: Optional[float] = None
    return_on_equity_ttm: Optional[float] = None
    revenue_ttm: Optional[float] = None
    gross_profit_ttm: Optional[float] = None
    diluted_eps_ttm: Optional[float] = None
    quarterly_earnings_growth_yoy: Optional[float] = None
    quarterly_revenue_growth_yoy: Optional[float] = None
    analyst_target_price: Optional[float] = None
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    price_to_sales_ratio_ttm: Optional[float] = None
    price_to_book_ratio: Optional[float] = None
    ev_to_revenue: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    beta: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    day_50_moving_average: Optional[float] = None
    day_200_moving_average: Optional[float] = None


class OptionContract(BaseModel):
    """Option contract data."""

    symbol: str
    underlying_symbol: str
    name: Optional[str] = None
    status: Optional[str] = None
    tradable: Optional[bool] = None
    expiration_date: Optional[str] = None
    root_symbol: Optional[str] = None
    underlying_asset_id: Optional[str] = None
    type: Optional[ContractType] = None
    style: Optional[ExerciseStyle] = None
    strike_price: Optional[str] = None
    multiplier: Optional[str] = None
    size: Optional[str] = None
    open_interest: Optional[int] = None
    open_interest_date: Optional[str] = None
    close_price: Optional[str] = None
    close_price_date: Optional[str] = None


class OptionLeg(BaseModel):
    """Option leg for multi-leg orders."""

    symbol: str
    ratio_qty: float
    side: Optional[OrderSide] = None
    position_intent: Optional[PositionIntent] = None


class OptionPosition(BaseModel):
    """Option position data."""

    symbol: str
    quantity: float
    side: str
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_plpc: float
    current_price: Optional[float] = None
    contract_type: Optional[ContractType] = None
    strike_price: Optional[float] = None
    expiration_date: Optional[str] = None


class NewsArticle(BaseModel):
    """News article data."""

    title: str
    url: str
    time_published: datetime
    summary: Optional[str] = None
    source: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    topics: Optional[List[str]] = None
    tickers: Optional[List[str]] = None


class TechnicalIndicatorResult(BaseModel):
    """Technical indicator result."""

    indicator: str
    symbol: str
    timestamp: datetime
    values: Dict[str, float]
    interpretation: Optional[str] = None


# Request Models
class PlaceOrderRequest(BaseModel):
    """Request to place an order."""

    symbol: str
    qty: float
    side: OrderSide
    order_type: OrderType
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "gtc"  # good_till_canceled


class GetBarsRequest(BaseModel):
    """Request for historical bar data."""

    symbols: List[str]
    timeframe: TimeFrame
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    limit: Optional[int] = Field(default=100, le=10000)


class GetTechnicalIndicatorRequest(BaseModel):
    """Request for technical indicator data."""

    symbol: str
    indicator: TechnicalIndicator
    timeframe: TimeFrame = TimeFrame.DAILY
    period: int = 14
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class GetNewsRequest(BaseModel):
    """Request for news data."""

    tickers: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    time_from: Optional[datetime] = None
    time_to: Optional[datetime] = None
    limit: int = Field(default=10, le=50)
    sentiment: Optional[str] = None  # "Bullish", "Bearish", "Neutral"


class PortfolioAnalysisRequest(BaseModel):
    """Request for portfolio analysis."""

    symbols: List[str]
    weights: Optional[List[float]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    benchmark: str = "SPY"


# Response Models
class MCPResponse(BaseModel):
    """Base MCP response."""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QuotesResponse(MCPResponse):
    """Response for quotes request."""

    data: Optional[List[QuoteData]] = None


class BarsResponse(MCPResponse):
    """Response for bars request."""

    data: Optional[List[BarData]] = None


class PositionsResponse(MCPResponse):
    """Response for positions request."""

    data: Optional[List[Position]] = None


class OrdersResponse(MCPResponse):
    """Response for orders request."""

    data: Optional[List[Order]] = None


class OrderResponse(MCPResponse):
    """Response for single order request."""

    data: Optional[Order] = None


class AccountResponse(MCPResponse):
    """Response for account request."""

    data: Optional[AccountInfo] = None


class CompanyResponse(MCPResponse):
    """Response for company data request."""

    data: Optional[CompanyOverview] = None


class NewsResponse(MCPResponse):
    """Response for news request."""

    data: Optional[List[NewsArticle]] = None


class TechnicalIndicatorResponse(MCPResponse):
    """Response for technical indicator request."""

    data: Optional[List[TechnicalIndicatorResult]] = None


class OptionContractsResponse(MCPResponse):
    """Response for option contracts request."""

    data: Optional[List[OptionContract]] = None


class OptionPositionsResponse(MCPResponse):
    """Response for option positions request."""

    data: Optional[List[OptionPosition]] = None
