#!/usr/bin/env python3
"""
Historical data request example for ezib_async.

Demonstrates:
- Requesting historical data using ib_async directly
- Different data resolutions and time ranges
- Working with historical bars
"""

import asyncio
from ezib_async import ezIBAsync


async def main():
    """Historical data request example."""
    ezib = ezIBAsync()
    
    try:
        # Connect to IB
        print("Connecting to IB...")
        await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
        
        if not ezib.connected:
            print("Failed to connect")
            return
            
        print("Connected! Creating contract...")
        
        # Create contract
        contract = await ezib.createStockContract("AAPL")
        print(f"Created contract: {contract.symbol}")
        
        # Check if ezib_async has historical data method
        if hasattr(ezib, 'requestHistoricalData'):
            print("Using ezib_async requestHistoricalData...")
            data = await ezib.requestHistoricalData(
                contracts=[contract],
                resolution="1 min", 
                lookback="2 D"
            )
            if data is not None:
                print(f"Retrieved {len(data)} data points")
                print(data.tail())
        else:
            print("Using ib_async directly for historical data...")
            
            # Use underlying ib_async for historical data
            ib = ezib.ib
            bars = await ib.reqHistoricalDataAsync(
                contract,
                endDateTime='',
                durationStr='2 D',
                barSizeSetting='1 min',
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            
            if bars:
                print(f"Retrieved {len(bars)} historical bars")
                print("\nLast 5 bars:")
                for bar in bars[-5:]:
                    print(f"{bar.date}: O={bar.open} H={bar.high} L={bar.low} C={bar.close}")
            else:
                print("No historical data received")
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        if ezib.connected:
            ezib.disconnect()
            print("Disconnected")


if __name__ == "__main__":
    asyncio.run(main())