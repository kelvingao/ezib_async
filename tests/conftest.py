#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Common test fixtures for unit tests.

These fixtures are optimized for fast, isolated unit tests that don't
require external dependencies like IB Gateway/TWS.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, Mock
from datetime import datetime, timedelta

from ezib_async import ezIBAsync
from ib_async import Stock, Option, Future, Forex, Index, Order, Contract, Trade

# Connection parameters
IB_HOST = 'localhost'
IB_PORT = 4001
IB_CLIENT_ID = 999

def pytest_addoption(parser):
    """Add custom command line options for pytest."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require a running IB Gateway/TWS"
    )

def pytest_configure(config):
    config.option.asyncio_default_fixture_loop_scope = "function"
    
    # Add custom markers
    config.addinivalue_line(
        "markers", "integration: marks tests as requiring IB Gateway/TWS connection"
    )

@pytest_asyncio.fixture
async def ezib_instance():
    """
    Fixture that provides a connected ezIBAsync instance.
    
    This fixture can be used by any test that needs a connected IB client.
    It will automatically handle connection and disconnection.
    """
    # Create ezIBAsync instance
    ezib = ezIBAsync(ibhost=IB_HOST, ibport=IB_PORT, ibclient=IB_CLIENT_ID)
    
    try:
        # Connect to IB Gateway/TWS
        connected = await ezib.connectAsync()
        
        if not ezib.connected:
            pytest.skip("Could not connect to IB Gateway/TWS. Skipping integration test.")
        
        # Return the connected instance
        yield ezib
        
    finally:
        # Disconnect when done
        if ezib and ezib.connected:
            ezib.disconnect()


# Mock Contract Fixtures
@pytest.fixture
def mock_stock_contract():
    """Stock contract fixture for testing."""
    return Stock(symbol="AAPL", exchange="SMART", currency="USD")


@pytest.fixture
def mock_option_contract():
    """Option contract fixture for testing."""
    # Use a date that's always in the future for testing
    future_date = (datetime.now() + timedelta(days=30)).strftime("%Y%m%d")
    return Option(
        symbol="SPY",
        lastTradeDateOrContractMonth=future_date,
        strike=500.0,
        right="C",
        exchange="SMART",
        currency="USD"
    )


@pytest.fixture
def mock_future_contract():
    """Future contract fixture for testing."""
    # Use a date that's always in the future for testing
    future_date = (datetime.now() + timedelta(days=90)).strftime("%Y%m")
    return Future(
        symbol="ES",
        lastTradeDateOrContractMonth=future_date,
        exchange="GLOBEX",
        currency="USD"
    )


@pytest.fixture
def mock_forex_contract():
    """Forex contract fixture for testing."""
    return Forex(pair="EURUSD", symbol="EUR", currency="USD", exchange="IDEALPRO")


@pytest.fixture
def mock_index_contract():
    """Index contract fixture for testing."""
    return Index(symbol="SPX", exchange="CBOE", currency="USD")


# Mock Order Fixtures
@pytest.fixture
def mock_market_order():
    """Market order fixture for testing."""
    order = Order()
    order.action = "BUY"
    order.totalQuantity = 100
    order.orderType = "MKT"
    order.orderId = 1001
    return order


@pytest.fixture
def mock_limit_order():
    """Limit order fixture for testing."""
    order = Order()
    order.action = "BUY"
    order.totalQuantity = 100
    order.orderType = "LMT"
    order.lmtPrice = 150.0
    order.orderId = 1002
    return order


@pytest.fixture
def mock_stop_order():
    """Stop order fixture for testing."""
    order = Order()
    order.action = "SELL"
    order.totalQuantity = 100
    order.orderType = "STP"
    order.auxPrice = 140.0
    order.orderId = 1003
    return order


# Mock ezIBAsync Instance for Unit Tests
@pytest_asyncio.fixture
async def mock_ezib():
    """Mocked ezIBAsync instance for unit tests."""
    ezib = MagicMock(spec=ezIBAsync)
    
    # Mock basic properties
    ezib.connected = True
    ezib._ibhost = IB_HOST
    ezib._ibport = IB_PORT
    ezib._ibclient = IB_CLIENT_ID
    ezib._default_account = "DU123456"
    
    # Mock async methods
    ezib.connectAsync = AsyncMock(return_value=True)
    ezib.createContract = AsyncMock()
    ezib.createStockContract = AsyncMock()
    ezib.createOptionContract = AsyncMock()
    ezib.createFuturesContract = AsyncMock()
    ezib.createForexContract = AsyncMock()
    ezib.requestMarketData = AsyncMock()
    ezib.requestContractDetails = AsyncMock()
    
    # Mock sync methods
    ezib.disconnect = Mock()
    ezib.createOrder = Mock()
    ezib.placeOrder = Mock()
    ezib.cancelMarketData = Mock()
    ezib.requestMarketDepth = Mock()
    ezib.cancelMarketDepth = Mock()
    
    # Mock data structures
    ezib.contracts = []
    ezib.orders = {}
    ezib.marketData = {}
    ezib.marketDepthData = {}
    ezib.optionsData = {}
    ezib.tickerIds = {0: "SYMBOL"}
    ezib._accounts = {"DU123456": {}}
    ezib._positions = {"DU123456": {}}
    ezib._portfolios = {"DU123456": {}}
    
    # Mock IB client
    ezib.ib = MagicMock()
    ezib.ib.connectAsync = AsyncMock(return_value=True)
    ezib.ib.qualifyContractsAsync = AsyncMock(return_value=[Mock()])
    ezib.ib.reqMktData = Mock()
    ezib.ib.reqMktDepth = Mock()
    ezib.ib.placeOrder = Mock(return_value=Mock(spec=Trade))
    
    return ezib


# Mock Trade Object
@pytest.fixture
def mock_trade():
    """Mock Trade object for order testing."""
    trade = Mock(spec=Trade)
    trade.order = Mock(spec=Order)
    trade.order.orderId = 1001
    trade.orderStatus = Mock()
    trade.orderStatus.status = "Submitted"
    return trade


# Helper functions for test data
def create_mock_ticker(symbol="AAPL", bid=150.0, ask=150.5, last=150.25):
    """Create a mock ticker object for testing market data."""
    ticker = Mock()
    ticker.contract = Mock()
    ticker.contract.symbol = symbol
    ticker.contract.secType = "STK"
    ticker.bid = bid
    ticker.ask = ask
    ticker.last = last
    ticker.bidSize = 100
    ticker.askSize = 100
    ticker.lastSize = 50
    ticker.time = datetime.now()
    ticker.domBids = []
    ticker.domAsks = []
    return ticker


def create_mock_account_value(tag="NetLiquidation", value="100000.0", currency="USD", account="DU123456"):
    """Create a mock AccountValue object for testing."""
    from ib_async import AccountValue
    return AccountValue(account=account, tag=tag, value=value, currency=currency, modelCode="")


def create_mock_position(symbol="AAPL", position=100, avg_cost=150.0, account="DU123456"):
    """Create a mock Position object for testing."""
    from ib_async import Position
    contract = Stock(symbol=symbol, exchange="SMART", currency="USD")
    return Position(account=account, contract=contract, position=position, avgCost=avg_cost)


def create_mock_portfolio_item(symbol="AAPL", position=100, market_price=150.0, 
                              market_value=15000.0, avg_cost=145.0, 
                              unrealized_pnl=500.0, realized_pnl=0.0, account="DU123456"):
    """Create a mock PortfolioItem object for testing."""
    from ib_async import PortfolioItem
    contract = Stock(symbol=symbol, exchange="SMART", currency="USD")
    return PortfolioItem(
        contract=contract,
        position=position,
        marketPrice=market_price,
        marketValue=market_value,
        averageCost=avg_cost,
        unrealizedPNL=unrealized_pnl,
        realizedPNL=realized_pnl,
        account=account
    )


def pytest_addoption(parser):
    """Add command line options for test execution."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require IB Gateway/TWS"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to handle integration tests.
    Skip integration tests unless --run-integration flag is used.
    """
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="Integration tests skipped (use --run-integration to run)")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)