#!/usr/bin/env python3
"""
Market data request example for ezib_async.

Demonstrates:
- Creating different contract types
- Requesting real-time market data
- Accessing market data properties
"""

import asyncio
from ezib_async import ezIBAsync


async def main():
    """Market data request example."""
    ezib = ezIBAsync()
    
    try:
        # Connect to IB
        print("Connecting to IB...")
        await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
        
        if not ezib.connected:
            print("Failed to connect")
            return
            
        print("Connected! Creating contracts...")
        
        # Create contracts
        contracts = await asyncio.gather(
            ezib.createStockContract("AAPL"),
            ezib.createFuturesContract("ES", expiry="202512"),
            ezib.createForexContract("EUR", currency="USD"),
            ezib.createOptionContract("AAPL", expiry="20251219", strike=200, otype="C")
        )
        
        print(f"Created {len(contracts)} contracts")
        
        # Request market data
        print("Requesting market data...")
        await ezib.requestMarketData(contracts)
        
        # Wait for data
        print("Waiting for data (15 seconds)...")
        await asyncio.sleep(15)
        
        # Display results
        print(f"\n{'='*40}")
        print("MARKET DATA RESULTS")
        print(f"{'='*40}")
        
        for contract in contracts:
            symbol = contract.symbol
            if symbol in ezib.marketData:
                data = ezib.marketData[symbol]
                print(f"\n{symbol} ({contract.secType}):")
                print(f"  Bid: {data.get('bid', 'N/A')}")
                print(f"  Ask: {data.get('ask', 'N/A')}")
                print(f"  Last: {data.get('last', 'N/A')}")
            else:
                print(f"\n{symbol}: No data received")
        
        # Cancel requests
        ezib.cancelMarketData(contracts)
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        if ezib.connected:
            ezib.disconnect()
            print("Disconnected")


if __name__ == "__main__":
    asyncio.run(main())