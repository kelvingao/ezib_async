# ezib_async Examples

This directory contains comprehensive examples demonstrating the capabilities of ezib_async, an asynchronous Python wrapper for Interactive Brokers API.


## Safety Notice

⚠️ **IMPORTANT**: These examples place real orders! Always use a paper trading account for testing.

Most order-related examples are commented out by default. Uncomment the `asyncio.run(main())` line to execute them.

## Examples Overview

### Market Data (`market_data.py`)
**Purpose**: Request and display real-time market data
**Demonstrates**:
- Creating different contract types (stocks, futures, forex, options)
- Requesting real-time market data
- Accessing market data through ezib properties
- Canceling market data requests

**Key Learning**: Understanding ezib_async's market data architecture

### Historical Data (`historical_data.py`)
**Purpose**: Retrieve historical price data
**Demonstrates**:
- Requesting historical data with different timeframes
- Working with pandas DataFrames
- Fallback to direct ib_async usage
- Data analysis and statistics

**Note**: Historical data functionality may require implementation in ezib_async

### Submit Order (`submit_order.py`)
**Purpose**: Place market and limit orders
**Demonstrates**:
- Creating market orders
- Creating limit orders with dynamic pricing
- Monitoring order status
- Viewing positions after execution

**⚠️ Places Real Orders**: Uncomment to run

### Bracket Order (`bracket_order.py`)
**Purpose**: Advanced order management with profit targets and stop losses
**Demonstrates**:
- Creating bracket orders (entry + target + stop)
- Manual bracket order implementation
- Risk management techniques
- Order relationship management

**⚠️ Places Real Orders**: Uncomment to run

### Account Info (`account_info.py`)
**Purpose**: Access account and portfolio information
**Demonstrates**:
- Viewing account details and balances
- Portfolio information
- Position tracking
- Order history
- Account update subscriptions

**Safe to Run**: Read-only operations

### Market Depth (`market_depth.py`)
**Purpose**: Access Level II market data
**Demonstrates**:
- Requesting market depth (order book)
- Viewing bid/ask levels
- Understanding Level II data structure
- Market microstructure analysis

**Note**: Requires market depth subscriptions

### Combo Orders (`combo_orders.py`)
**Purpose**: Options spread trading
**Demonstrates**:
- Creating option contracts
- Building combo legs for spreads
- Bull call spread example
- Credit/debit spread concepts
- Manual spread implementation

**⚠️ Places Real Orders**: Uncomment to run
**Note**: Requires options trading permissions

### Custom Callbacks (`custom_callbacks.py`)
**Purpose**: Event-driven trading with custom handlers
**Demonstrates**:
- Setting up custom callback functions
- Order status monitoring
- Market data event handling
- Building trading bots with event responses
- Price alerts and triggers

**⚠️ Places Test Order**: Uncomment to run