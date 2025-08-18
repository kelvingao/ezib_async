#!/usr/bin/env python3
"""
Historical data request example for ezib_async.
"""

import asyncio
from ezib_async import ezIBAsync


async def main():
    """Historical data request example."""
    
    # Initialize ezib_async
    ezib = ezIBAsync()
    
    try:
        # Connect to IB Gateway
        print("Connecting to IB Gateway...")
        await ezib.connectAsync(ibclient=100, ibhost="localhost", ibport=4001)
        
        if not ezib.connected:
            print("Failed to connect")
            return
        
        print("Connected successfully!")
        
        # Create a contract
        contract = await ezib.createStockContract("AAPL")
        print(f"Created contract for {contract.symbol}")
        
        # Request 2 days of 1 minute data and save it to current directory
        print("\nRequesting historical data...")
        bars = await ezib.requestHistoricalData(
            contracts=contract,
            resolution="1 min", 
            lookback="2 D",
            csv_path='aapl_1min_data.csv'
        )
        
        if bars:
            print(f"✅ Retrieved {len(bars)} bars of 1-minute data")
            print(f"📁 Data saved to: aapl_1min_data.csv")
            
            # Show last 5 bars
            print("\nLast 5 bars:")
            for bar in bars[-5:]:
                print(f"  {bar.date}: Close=${bar.close:.2f} Volume={bar.volume:,}")
            
            # Show data summary
            from ib_async import util
            df = util.df(bars)
            print("\nData Summary:")
            print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"  Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
            print(f"  Total volume: {df['volume'].sum():,}")
        else:
            print("No data received")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Disconnect when done
        if ezib.connected:
            ezib.disconnect()
            print("\nDisconnected from IB Gateway")


if __name__ == "__main__":
    asyncio.run(main())