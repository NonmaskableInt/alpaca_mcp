"""Tests for AlphaVantage integration tools."""

import pytest
from unittest.mock import patch


class TestGetTechnicalIndicators:
    """Tests for get_technical_indicators function."""

    async def test_rsi_default_params(self, server, mock_alphavantage_rsi_data):
        """Test getting RSI with default parameters."""
        with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_rsi_data):
            tools = server.app._tool_manager._tools
            fn = tools["get_technical_indicators"].fn

            result = await fn(symbol="NVDA")

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 2
        assert result.data[0].indicator == "RSI"
        assert result.data[0].symbol == "NVDA"
        assert "RSI" in result.data[0].values
        assert result.data[0].values["RSI"] == pytest.approx(65.5234)

    async def test_rsi_explicit_params(self, server, mock_alphavantage_rsi_data):
        """Test getting RSI with explicit symbol, time_period, and timeframe."""
        with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_rsi_data) as mock_req:
            tools = server.app._tool_manager._tools
            fn = tools["get_technical_indicators"].fn

            result = await fn(symbol="NVDA", indicator="RSI", time_period=14, timeframe="1Day")

        assert result.success is True
        call_params = mock_req.call_args[0][0]
        assert call_params["function"] == "RSI"
        assert call_params["symbol"] == "NVDA"
        assert call_params["time_period"] == "14"
        assert call_params["interval"] == "daily"

    async def test_symbol_uppercased(self, server, mock_alphavantage_rsi_data):
        """Test that symbol is uppercased before the API call."""
        with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_rsi_data) as mock_req:
            tools = server.app._tool_manager._tools
            fn = tools["get_technical_indicators"].fn

            result = await fn(symbol="nvda")

        assert result.success is True
        assert result.data[0].symbol == "NVDA"
        assert mock_req.call_args[0][0]["symbol"] == "NVDA"

    async def test_timeframe_mapping(self, server, mock_alphavantage_rsi_data):
        """Test that timeframe values are mapped to AlphaVantage intervals."""
        timeframe_cases = [
            ("1Min", "1min"),
            ("5Min", "5min"),
            ("15Min", "15min"),
            ("30Min", "30min"),
            ("1Hour", "60min"),
            ("1Day", "daily"),
            ("1Week", "weekly"),
            ("1Month", "monthly"),
        ]
        tools = server.app._tool_manager._tools
        fn = tools["get_technical_indicators"].fn

        for timeframe, expected_interval in timeframe_cases:
            with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_rsi_data) as mock_req:
                await fn(symbol="NVDA", timeframe=timeframe)
                assert mock_req.call_args[0][0]["interval"] == expected_interval, (
                    f"timeframe {timeframe!r} should map to {expected_interval!r}"
                )

    async def test_missing_api_key(self, server):
        """Test error returned when ALPHAVANTAGE_API_KEY is not set."""
        server.alphavantage_api_key = None
        tools = server.app._tool_manager._tools
        fn = tools["get_technical_indicators"].fn

        result = await fn(symbol="NVDA")

        assert result.success is False
        assert "ALPHAVANTAGE_API_KEY" in result.error

    async def test_api_error(self, server):
        """Test that API errors are returned as failure responses."""
        with patch.object(server, "_alphavantage_request", side_effect=Exception("Invalid API call")):
            tools = server.app._tool_manager._tools
            fn = tools["get_technical_indicators"].fn

            result = await fn(symbol="NVDA")

        assert result.success is False
        assert "Invalid API call" in result.error

    async def test_missing_analysis_key_in_response(self, server):
        """Test graceful handling when indicator key is missing from response."""
        with patch.object(server, "_alphavantage_request", return_value={"Meta Data": {}}):
            tools = server.app._tool_manager._tools
            fn = tools["get_technical_indicators"].fn

            result = await fn(symbol="NVDA", indicator="RSI")

        assert result.success is False
        assert "RSI" in result.error


class TestGetDailyPrices:
    """Tests for get_daily_prices function."""

    async def test_default_params(self, server, mock_alphavantage_daily_data):
        """Test getting daily prices with default parameters."""
        with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_daily_data):
            tools = server.app._tool_manager._tools
            fn = tools["get_daily_prices"].fn

            result = await fn(symbol="NVDA")

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 2
        bar = result.data[0]
        assert bar.symbol == "NVDA"
        assert bar.open == 470.0
        assert bar.high == 490.0
        assert bar.low == 465.0
        assert bar.close == 485.0
        assert bar.volume == 50000000

    async def test_outputsize_param_passed(self, server, mock_alphavantage_daily_data):
        """Test that outputsize is forwarded to the API."""
        with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_daily_data) as mock_req:
            tools = server.app._tool_manager._tools
            fn = tools["get_daily_prices"].fn

            await fn(symbol="NVDA", outputsize="compact")

        call_params = mock_req.call_args[0][0]
        assert call_params["function"] == "TIME_SERIES_DAILY"
        assert call_params["symbol"] == "NVDA"
        assert call_params["outputsize"] == "compact"

    async def test_symbol_uppercased(self, server, mock_alphavantage_daily_data):
        """Test that symbol is uppercased."""
        with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_daily_data) as mock_req:
            tools = server.app._tool_manager._tools
            fn = tools["get_daily_prices"].fn

            result = await fn(symbol="nvda")

        assert result.success is True
        assert mock_req.call_args[0][0]["symbol"] == "NVDA"
        assert result.data[0].symbol == "NVDA"

    async def test_missing_time_series_key(self, server):
        """Test error when time series key is missing from response."""
        with patch.object(server, "_alphavantage_request", return_value={"Meta Data": {}}):
            tools = server.app._tool_manager._tools
            fn = tools["get_daily_prices"].fn

            result = await fn(symbol="NVDA")

        assert result.success is False
        assert "No daily price data found" in result.error

    async def test_api_error(self, server):
        """Test that API errors are returned as failure responses."""
        with patch.object(server, "_alphavantage_request", side_effect=Exception("Rate limit")):
            tools = server.app._tool_manager._tools
            fn = tools["get_daily_prices"].fn

            result = await fn(symbol="NVDA")

        assert result.success is False
        assert "Rate limit" in result.error

    async def test_missing_api_key(self, server):
        """Test error returned when ALPHAVANTAGE_API_KEY is not set."""
        server.alphavantage_api_key = None
        tools = server.app._tool_manager._tools
        fn = tools["get_daily_prices"].fn

        result = await fn(symbol="NVDA")

        assert result.success is False
        assert "ALPHAVANTAGE_API_KEY" in result.error


class TestGetIntradayPrices:
    """Tests for get_intraday_prices function."""

    async def test_default_params(self, server, mock_alphavantage_intraday_data):
        """Test getting intraday prices with default parameters."""
        with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_intraday_data):
            tools = server.app._tool_manager._tools
            fn = tools["get_intraday_prices"].fn

            result = await fn(symbol="NVDA")

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 2
        bar = result.data[0]
        assert bar.symbol == "NVDA"
        assert bar.open == 470.0
        assert bar.high == 471.0
        assert bar.low == 469.0
        assert bar.close == 470.5
        assert bar.volume == 100000

    async def test_explicit_params(self, server, mock_alphavantage_intraday_data):
        """Test getting intraday prices with explicit symbol, timeframe, outputsize."""
        with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_intraday_data) as mock_req:
            tools = server.app._tool_manager._tools
            fn = tools["get_intraday_prices"].fn

            result = await fn(symbol="NVDA", timeframe="5Min", outputsize="compact")

        assert result.success is True
        call_params = mock_req.call_args[0][0]
        assert call_params["function"] == "TIME_SERIES_INTRADAY"
        assert call_params["symbol"] == "NVDA"
        assert call_params["interval"] == "5min"
        assert call_params["outputsize"] == "compact"

    async def test_timeframe_mapping(self, server, mock_alphavantage_intraday_data):
        """Test intraday timeframe values map to correct AlphaVantage intervals."""
        timeframe_cases = [
            ("1Min", "1min"),
            ("5Min", "5min"),
            ("15Min", "15min"),
            ("30Min", "30min"),
            ("1Hour", "60min"),
        ]
        tools = server.app._tool_manager._tools
        fn = tools["get_intraday_prices"].fn

        for timeframe, expected_interval in timeframe_cases:
            # Patch with matching time series key
            response = {
                "Meta Data": {},
                f"Time Series ({expected_interval})": {
                    "2024-01-19 15:55:00": {
                        "1. open": "470.0",
                        "2. high": "471.0",
                        "3. low": "469.0",
                        "4. close": "470.5",
                        "5. volume": "100000",
                    }
                },
            }
            with patch.object(server, "_alphavantage_request", return_value=response) as mock_req:
                result = await fn(symbol="NVDA", timeframe=timeframe)
                assert result.success is True
                assert mock_req.call_args[0][0]["interval"] == expected_interval

    async def test_missing_time_series_key(self, server):
        """Test error when time series key is missing from response."""
        with patch.object(server, "_alphavantage_request", return_value={"Meta Data": {}}):
            tools = server.app._tool_manager._tools
            fn = tools["get_intraday_prices"].fn

            result = await fn(symbol="NVDA", timeframe="5Min")

        assert result.success is False
        assert "5min" in result.error

    async def test_api_error(self, server):
        """Test that API errors are returned as failure responses."""
        with patch.object(server, "_alphavantage_request", side_effect=Exception("API Error")):
            tools = server.app._tool_manager._tools
            fn = tools["get_intraday_prices"].fn

            result = await fn(symbol="NVDA")

        assert result.success is False
        assert "API Error" in result.error

    async def test_missing_api_key(self, server):
        """Test error returned when ALPHAVANTAGE_API_KEY is not set."""
        server.alphavantage_api_key = None
        tools = server.app._tool_manager._tools
        fn = tools["get_intraday_prices"].fn

        result = await fn(symbol="NVDA")

        assert result.success is False
        assert "ALPHAVANTAGE_API_KEY" in result.error


class TestGetMarketNews:
    """Tests for get_market_news function."""

    async def test_single_ticker(self, server, mock_alphavantage_news_data):
        """Test getting news for a single ticker."""
        with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_news_data):
            tools = server.app._tool_manager._tools
            fn = tools["get_market_news"].fn

            result = await fn(tickers=["NVDA"], limit=3)

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1
        article = result.data[0]
        assert article.title == "NVIDIA Reports Record Earnings"
        assert article.source == "Reuters"
        assert article.sentiment_label == "Bullish"
        assert article.sentiment_score == pytest.approx(0.65)
        assert "NVDA" in article.tickers
        assert "Technology" in article.topics

    async def test_tickers_uppercased(self, server, mock_alphavantage_news_data):
        """Test that ticker symbols are uppercased."""
        with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_news_data) as mock_req:
            tools = server.app._tool_manager._tools
            fn = tools["get_market_news"].fn

            await fn(tickers=["nvda"])

        call_params = mock_req.call_args[0][0]
        assert call_params["tickers"] == "NVDA"

    async def test_limit_capped_at_50(self, server, mock_alphavantage_news_data):
        """Test that limit is capped at 50."""
        with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_news_data) as mock_req:
            tools = server.app._tool_manager._tools
            fn = tools["get_market_news"].fn

            await fn(tickers=["NVDA"], limit=100)

        call_params = mock_req.call_args[0][0]
        assert call_params["limit"] == "50"

    async def test_no_tickers_omits_param(self, server, mock_alphavantage_news_data):
        """Test that tickers param is omitted when not provided."""
        with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_news_data) as mock_req:
            tools = server.app._tool_manager._tools
            fn = tools["get_market_news"].fn

            result = await fn()

        assert result.success is True
        call_params = mock_req.call_args[0][0]
        assert "tickers" not in call_params

    async def test_empty_feed_returns_empty_list(self, server):
        """Test that a response with no feed returns an empty list."""
        with patch.object(server, "_alphavantage_request", return_value={"items": "0"}):
            tools = server.app._tool_manager._tools
            fn = tools["get_market_news"].fn

            result = await fn(tickers=["NVDA"])

        assert result.success is True
        assert result.data == []

    async def test_api_error(self, server):
        """Test that API errors are returned as failure responses."""
        with patch.object(server, "_alphavantage_request", side_effect=Exception("Invalid ticker")):
            tools = server.app._tool_manager._tools
            fn = tools["get_market_news"].fn

            result = await fn(tickers=["NVDA"])

        assert result.success is False
        assert "Invalid ticker" in result.error

    async def test_missing_api_key(self, server):
        """Test error returned when ALPHAVANTAGE_API_KEY is not set."""
        server.alphavantage_api_key = None
        tools = server.app._tool_manager._tools
        fn = tools["get_market_news"].fn

        result = await fn(tickers=["NVDA"])

        assert result.success is False
        assert "ALPHAVANTAGE_API_KEY" in result.error

    async def test_time_published_parsed(self, server, mock_alphavantage_news_data):
        """Test that time_published is correctly parsed."""
        with patch.object(server, "_alphavantage_request", return_value=mock_alphavantage_news_data):
            tools = server.app._tool_manager._tools
            fn = tools["get_market_news"].fn

            result = await fn(tickers=["NVDA"])

        assert result.success is True
        ts = result.data[0].time_published
        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 19
        assert ts.hour == 15


class TestAlphavantageRequestHelper:
    """Tests for the _alphavantage_request helper method."""

    def test_raises_when_api_key_missing(self, server):
        """Test ValueError raised when ALPHAVANTAGE_API_KEY is not set."""
        server.alphavantage_api_key = None
        with pytest.raises(ValueError, match="ALPHAVANTAGE_API_KEY"):
            server._alphavantage_request({"function": "RSI"})

    def test_raises_on_error_message(self, server):
        """Test ValueError raised when response contains Error Message."""
        import json
        from io import BytesIO
        from unittest.mock import MagicMock

        error_response = {"Error Message": "Invalid API call."}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(error_response).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(ValueError, match="Invalid API call"):
                server._alphavantage_request({"function": "RSI", "symbol": "NVDA"})

    def test_raises_on_rate_limit_note(self, server):
        """Test ValueError raised on AlphaVantage rate limit Note."""
        import json
        from unittest.mock import MagicMock

        note_response = {"Note": "Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day."}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(note_response).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(ValueError, match="rate limit"):
                server._alphavantage_request({"function": "RSI", "symbol": "NVDA"})
