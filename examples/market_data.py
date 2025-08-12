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
            ticker_id = ezib.tickerId(ezib.contractString(contract))
            is_option = contract.secType in ("OPT", "FOP")
            
            # Choose the correct data source based on contract type
            data_source = ezib.optionsData if is_option else ezib.marketData
            
            if ticker_id in data_source:
                data = data_source[ticker_id]
                print(f"\n{symbol} ({contract.secType}):")
                
                # Extract latest data from DataFrame
                if hasattr(data, 'iloc') and len(data) > 0:
                    latest = data.iloc[-1]
                    print(f"  Bid: {latest.get('bid', 'N/A')}")
                    print(f"  Ask: {latest.get('ask', 'N/A')}")
                    print(f"  Last: {latest.get('last', 'N/A')}")
                    print(f"  Bid Size: {latest.get('bidsize', 'N/A')}")
                    print(f"  Ask Size: {latest.get('asksize', 'N/A')}")
                    print(f"  Last Size: {latest.get('lastsize', 'N/A')}")
                    
                    # Show additional data for options
                    if is_option:
                        print(f"  Implied Vol: {latest.get('iv', 'N/A')}")
                        print(f"  Delta: {latest.get('delta', 'N/A')}")
                        print(f"  Gamma: {latest.get('gamma', 'N/A')}")
                        print(f"  Open Interest: {latest.get('oi', 'N/A')}")
                else:
                    print(f"  Data format: {type(data)}")
            else:
                data_type = "optionsData" if is_option else "marketData"
                print(f"\n{symbol}: No data received (checked {data_type})")
        
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