# ezib_async

![Python version](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat)
![PyPi version](https://img.shields.io/pypi/v/ezib_async.svg?maxAge=60)
![PyPi status](https://img.shields.io/pypi/status/ezib_async.svg?maxAge=60)

An asynchronous Python wrapper for Interactive Brokers API based on ib_async, providing a more Pythonic and asyncio-friendly interface.

## Features

- **Fully Asynchronous**: Built from the ground up with Python's asyncio for non-blocking operations
- **Event-Based Architecture**: Subscribe to market data and account updates
- **Multi-Account Support**: Support for multiple accounts
- **Simplified API**: Clean and easy-to-use API that reduces boilerplate code
- **Real-time Market Data**: Easily access real-time market data and market depth
- **Advanced Order Types**: Support for bracket orders, trailing stops, and other advanced order types
- **Historical Data Retrieval**: Flexible retrieval of historical market data

## Installation

```bash
# Using pip
pip install ezib-async

# Using uv (recommended)
uv pip install ezib-async
```

## Code Examples

### Request Market Data

```python
import asyncio
from ezib_async import ezIBpyAsync

async def main():
    ezib = ezIBpyAsync()
    await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
    
    # Create contracts
    stk_contract = await ezib.createStockContract("AAPL")
    fut_contract = await ezib.createFuturesContract("ES", expiry="202512")
    
    # Request market data
    await ezib.requestMarketData()
    
    # Wait for data
    await asyncio.sleep(10)
    
    # View market data
    print(ezib.marketData)
    
    # Cancel market data request and disconnect
    await ezib.cancelMarketData()
    ezib.disconnect()

asyncio.run(main())
```

### Submit an Order

```python
import asyncio
from ezib_async import ezIBpyAsync

async def main():
    ezib = ezIBpyAsync()
    await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
    
    # Create contract
    contract = await ezib.createStockContract("AAPL")
    
    # Create order
    order = await ezib.createOrder(quantity=1)  # Use price=X for limit orders
    
    # Place order (returns trade)
    trade = await ezib.placeOrder(contract, order)
    
    # Wait for order processing
    await asyncio.sleep(1)
    
    # View positions
    print("Positions:")
    print(ezib.positions)
    
    # Disconnect
    ezib.disconnect()

asyncio.run(main())
```

### Submit a Bracket Order

```python
import asyncio
from ezib_async import ezIBpyAsync

async def main():
    ezib = ezIBpyAsync()
    await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
    
    # Create contract
    contract = await ezib.createStockContract("AAPL")
    
    # Submit bracket order (entry=0 means market order)
    order = await ezib.createBracketOrder(
        contract, 
        quantity=1, 
        entry=0, 
        target=200.0, 
        stop=180.0
    )
    
    # Wait for order processing
    await asyncio.sleep(1)
    
    # View positions
    print("Positions:")
    print(ezib.positions)
    
    # Disconnect
    ezib.disconnect()

asyncio.run(main())
```

### Request Historical Data

```python
import asyncio
from ezib_async import ezIBpyAsync

async def main():
    ezib = ezIBpyAsync()
    await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
    
    # Create contract
    contract = await ezib.createStockContract("AAPL")
    
    # Request historical data
    data = await ezib.requestHistoricalData(
        resolution="1 min", 
        lookback="2 D"
    )
    
    print(data)
    
    # Disconnect
    ezib.disconnect()

asyncio.run(main())
```

## Account Information

ezib_async provides the following variables to access account and market information (auto-updating):

- `ezib.marketData`: Market data
- `ezib.marketDepthData`: Market depth data
- `ezib.account`: Account information
- `ezib.positions`: Position information
- `ezib.portfolio`: Portfolio information
- `ezib.contracts`: Contract information
- `ezib.orders`: Order information (by TickId)
- `ezib.symbol_orders`: Order information (by symbol)

## Logging

ezib_async uses standard Python logging facilities with a default log level of `ERROR`:

```python
import logging
import ezib_async

# Set log level
logging.getLogger('ezib_async').setLevel(logging.INFO)

# Initialize
ezib = ezib_async.ezIBpyAsync()
```

## Requirements

- Python 3.11+
- ib_async 1.0.3+
- Interactive Brokers TWS or Gateway

## License

[MIT License](LICENSE)