#!/usr/bin/env python3
"""
Market depth (Level II) data example for ezib_async.

Demonstrates:
- Requesting market depth data
- Viewing bid/ask book levels
- Using ib_async directly for market depth

Note: Requires market depth subscriptions and permissions.
"""

import asyncio
from ezib_async import ezIBAsync


async def main():
    """Market depth data example."""
    ezib = ezIBAsync()
    
    try:
        # Connect to IB
        print("Connecting to IB...")
        await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
        
        if not ezib.connected:
            print("Failed to connect")
            return
            
        print("Connected! Creating contracts...")
        
        # Create contracts (forex typically good for market depth)
        forex_contract = await ezib.createForexContract("EUR", currency="USD")
        stock_contract = await ezib.createStockContract("AAPL")
        
        contracts = [forex_contract, stock_contract]
        print(f"Created {len(contracts)} contracts")
        
        # Check if requestMarketDepth exists
        if hasattr(ezib, 'requestMarketDepth'):
            print("Using ezib_async requestMarketDepth...")
            await ezib.requestMarketDepth(contracts)
        else:
            print("Using ib_async directly for market depth...")
            
            # Use ib_async directly
            ib = ezib.ib
            for contract in contracts:
                ib.reqMktDepth(contract, numRows=10)
                print(f"Requested depth for {contract.symbol}")
        
        # Wait for market depth data
        print("Waiting for market depth data (30 seconds)...")
        
        for i in range(6):
            await asyncio.sleep(5)
            print(f"\n--- Update {i+1}/6 ---")
            
            # Display market depth data
            if hasattr(ezib, 'marketDepthData') and ezib.marketDepthData:
                for symbol, depth_data in ezib.marketDepthData.items():
                    print(f"{symbol} Depth: {depth_data}")
            else:
                print("No market depth data available")
                
            # Show regular market data for comparison
            for contract in contracts:
                if contract.symbol in ezib.marketData:
                    data = ezib.marketData[contract.symbol]
                    bid = data.get('bid', 'N/A')
                    ask = data.get('ask', 'N/A')
                    print(f"{contract.symbol}: Bid={bid} Ask={ask}")
        
        print(f"\n=== SUMMARY ===")
        print("Market depth requires:")
        print("- Market data subscriptions")
        print("- Level II data permissions")
        print("- Exchange-specific permissions")
        
        # Cancel requests
        if hasattr(ezib, 'cancelMarketDepth'):
            ezib.cancelMarketDepth(contracts)
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        if ezib.connected:
            ezib.disconnect()
            print("Disconnected")


if __name__ == "__main__":
    asyncio.run(main())