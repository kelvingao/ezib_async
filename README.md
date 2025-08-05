# ezib_async

![Python version](https://img.shields.io/badge/python-3.12+-blue.svg?style=flat)
![PyPi version](https://img.shields.io/pypi/v/ezib_async.svg?maxAge=60)
![PyPi status](https://img.shields.io/pypi/status/ezib_async.svg?maxAge=60)
![Coverage](https://img.shields.io/badge/coverage-74%25-orange.svg?style=flat)

**An Asynchronous Python Wrapper for Interactive Brokers API**

ezib_async is a modern, high-performance Python library that provides a clean, asyncio-based interface to Interactive Brokers' TWS API. Built on top of ib_async, it simplifies trading operations with a more Pythonic approach while maintaining full compatibility with IB's extensive feature set.

## 🏗️ Architecture Overview

```
┌─────────────────┐    asyncio    ┌─────────────────┐    IB API    ┌─────────────────┐
│   Your Trading  │◄──────────────┤   ezib_async    │◄─────────────┤ Interactive     │
│   Application   │               │    Wrapper      │              │ Brokers         │
│                 │               │                 │              │ TWS/Gateway     │
└─────────────────┘               └─────────────────┘              └─────────────────┘
         │                                 │
         │                                 │
         ▼                                 ▼
┌─────────────────┐               ┌─────────────────┐
│   Real-time     │               │   Auto-updating │
│   Market Data   │               │   Properties    │
│   • Stocks      │               │   • Positions   │
│   • Options     │               │   • Account     │
│   • Futures     │               │   • Portfolio   │
│   • Forex       │               │   • Orders      │
└─────────────────┘               └─────────────────┘
```

### Core Components

- **Contract Creation**: Simplified helpers for stocks, options, futures, and forex
- **Order Management**: Market, limit, stop, and bracket order support
- **Real-time Data**: Live market data with automatic updates
- **Event System**: Built on eventkit for responsive data handling
- **Account Tracking**: Auto-updating positions, portfolio, and account information

## 🚀 Features

- ✅ **Fully Asynchronous**: Built from the ground up with Python's asyncio
- ✅ **Clean API**: Simplified interface reduces boilerplate code significantly
- ✅ **Real-time Updates**: Auto-updating properties for market data and account info
- ✅ **Multi-Asset Support**: Stocks, options, futures, forex, and indices
- ✅ **Advanced Orders**: Market, limit, stop, trailing stops, and bracket orders
- ✅ **Event-Driven**: Subscribe to market data and account changes
- ✅ **Historical Data**: Flexible retrieval with multiple time frames
- ✅ **Production Ready**: Comprehensive error handling and logging

## 📋 Requirements

- **Python**: 3.12+ (enforced at runtime)
- **Interactive Brokers**: TWS or IB Gateway
- **Dependencies**: ib_async 2.0.1+

## 🛠️ Installation

```bash
# Using pip
pip install ezib-async

# Using uv (recommended)
uv pip install ezib-async

# Development installation
git clone https://github.com/kelvingao/ezib_async.git
cd ezib_async
uv pip install -e ".[dev]"
```

## 🏃‍♂️ Quick Start

### 1. Setup Interactive Brokers

#### TWS (Trader Workstation)
1. Enable API access: `Configure → API → Enable ActiveX and Socket Clients`
2. Set API port (7497 for live, 7496 for paper trading)
3. Disable "Read-Only API"

#### IB Gateway (Recommended)
1. Configure API settings (port 4001 for live, 4002 for paper)
2. Enable API access and disable read-only mode

### 2. Basic Usage

```python
import asyncio
from ezib_async import ezIBAsync

async def main():
    # Create and connect to IB
    ezib = ezIBAsync()
    await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
    
    # Create a stock contract
    contract = await ezib.createStockContract("AAPL")
    
    # Request real-time market data
    await ezib.requestMarketData([contract])
    
    # Wait for data and display
    await asyncio.sleep(5)
    print("Market Data:", ezib.marketData)
    
    # Clean up
    ezib.cancelMarketData([contract])
    ezib.disconnect()

asyncio.run(main())
```

## 📊 Usage Examples

### Market Data Streaming

```python
import asyncio
from ezib_async import ezIBAsync

async def stream_market_data():
    ezib = ezIBAsync()
    await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
    
    # Create multiple contracts
    contracts = await asyncio.gather(
        ezib.createStockContract("NVDA"),
        ezib.createStockContract("TSLA"),
        ezib.createOptionContract("AAPL", expiry="20251219", strike=200, otype="C"),
        ezib.createFuturesContract("ES", expiry="202512", exchange="CME"),
        ezib.createForexContract("EUR", currency="USD")
    )
    
    # Start streaming
    await ezib.requestMarketData(contracts)
    
    # Monitor real-time updates
    for i in range(60):  # Run for 1 minute
        await asyncio.sleep(1)
        
        # Access real-time data
        for symbol, data in ezib.marketData.items():
            if data and hasattr(data, 'last') and data.last:
                print(f"{symbol}: ${data.last:.2f}")
    
    # Cleanup
    ezib.cancelMarketData(contracts)
    ezib.disconnect()

asyncio.run(stream_market_data())
```

### Order Management

```python
import asyncio
from ezib_async import ezIBAsync

async def trading_example():
    ezib = ezIBAsync()
    await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
    
    # Create contract
    contract = await ezib.createStockContract("AAPL")
    
    # Market order
    market_order = await ezib.createOrder(quantity=100)
    trade = await ezib.placeOrder(contract, market_order)
    print(f"Market order placed: {trade}")
    
    # Limit order
    limit_order = await ezib.createOrder(quantity=100, price=150.00)
    trade = await ezib.placeOrder(contract, limit_order)
    print(f"Limit order placed: {trade}")
    
    # Bracket order (entry, profit target, stop loss)
    bracket_trades = await ezib.createBracketOrder(
        contract=contract,
        quantity=100,
        entry=0,  # Market entry
        target=160.00,  # Profit target
        stop=140.00     # Stop loss
    )
    print(f"Bracket order placed: {len(bracket_trades)} orders")
    
    # Monitor positions and orders
    await asyncio.sleep(2)
    print("Current Positions:", ezib.positions)
    print("Active Orders:", ezib.orders)
    
    ezib.disconnect()

asyncio.run(trading_example())
```

### Historical Data Analysis

```python
import asyncio
from ezib_async import ezIBAsync

async def get_historical_data():
    ezib = ezIBAsync()
    await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
    
    # Create contract
    contract = await ezib.createStockContract("AAPL")
    
    # Get daily bars for the last month
    daily_bars = await ezib.requestHistoricalData(
        contracts=[contract],
        resolution="1 day",
        lookback="30 D"
    )
    print("Daily bars:", daily_bars)
    
    # Get minute bars for today
    minute_bars = await ezib.requestHistoricalData(
        contracts=[contract],
        resolution="1 min",
        lookback="1 D"
    )
    print("Minute bars:", minute_bars)
    
    ezib.disconnect()

asyncio.run(get_historical_data())
```

### Account and Portfolio Monitoring

```python
import asyncio
from ezib_async import ezIBAsync

async def monitor_account():
    ezib = ezIBAsync()
    await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
    
    # Wait for account data to populate
    await asyncio.sleep(3)
    
    # Access account information
    print("Account Info:")
    for account_id, account_data in ezib.account.items():
        print(f"  Account: {account_id}")
        for key, value in account_data.items():
            print(f"    {key}: {value}")
    
    # Access positions
    print("\nPositions:")
    for account_id, positions in ezib.positions.items():
        print(f"  Account: {account_id}")
        for position in positions:
            print(f"    {position}")
    
    # Access portfolio
    print("\nPortfolio:")
    for account_id, portfolio in ezib.portfolio.items():
        print(f"  Account: {account_id}")
        for item in portfolio:
            print(f"    {item}")
    
    ezib.disconnect()

asyncio.run(monitor_account())
```

## 🔧 Configuration

### Connection Parameters

```python
ezib = ezIBAsync(
    ibhost="localhost",    # IB Gateway/TWS host
    ibport=4001,          # API port (4001 live, 4002 paper)
    ibclient=0,           # Unique client ID
    timeout=10            # Connection timeout
)
```

### Logging Configuration

```python
import logging
from ezib_async import ezIBAsync

# Set log level
logging.getLogger('ezib_async').setLevel(logging.INFO)

# Custom logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading.log'),
        logging.StreamHandler()
    ]
)

ezib = ezIBAsync()
```

## 📊 Data Access Properties

ezib_async provides auto-updating properties for real-time access:

```python
# Market data (real-time quotes and ticks)
ezib.marketData          # {symbol: ticker_object}
ezib.marketDepthData     # Market depth information

# Account information (auto-updated)
ezib.account            # Account values by account ID
ezib.positions          # Current positions by account
ezib.portfolio          # Portfolio items by account

# Contract and order tracking
ezib.contracts          # All contract objects
ezib.orders            # Orders by TickId
ezib.symbol_orders     # Orders grouped by symbol
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make changes and add tests
4. Run tests: `make test-coverage`
5. Run linting: `ruff check src/ tests/`
6. Commit changes: `git commit -m 'Add new feature'`
7. Push to branch: `git push origin feature/new-feature`
8. Submit a Pull Request

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-repo/ezib_async.git
cd ezib_async

# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
make test-coverage

# Run linting
ruff check src/ tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.