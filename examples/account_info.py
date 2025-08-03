#!/usr/bin/env python3
"""
Account information example for ezib_async.

Demonstrates:
- Requesting account information
- Viewing positions and portfolio
- Accessing account properties
"""

import asyncio
from ezib_async import ezIBAsync


async def main():
    # Initialize ezIBAsync client
    ezib = ezIBAsync()
    
    try:
        # Connect to IB Gateway/TWS
        await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=100)
        
        if not ezib.connected:
            print("Failed to connect to IB")
            return
            
        print("Connected! Waiting for account data (5 seconds)...")
        await asyncio.sleep(5)
        
        # Account Information
        print("\nAccount Information")
        print(ezib.account)
        
        # Positions 
        print("\nPositions")
        print(ezib.positions)
        
        # Portfolio
        print("\nPortfolio")
        print(ezib.portfolio)
        
        # Contracts
        print("\nContracts")
        print(ezib.contracts)
        
        # Orders by TickId
        print("\nOrders (by TickId)")
        print(ezib.orders)
        
        # Orders by Symbol
        print("\nOrders (by Symbol)")
        print(ezib.symbol_orders)
        
        # Summary
        print(f"\n{'='*50}")
        print("SUMMARY")
        print(f"{'='*50}")
        properties = [
            ('account', ezib.account),
            ('positions', ezib.positions),
            ('portfolio', ezib.portfolio), 
            ('contracts', ezib.contracts),
            ('orders', ezib.orders),
            ('symbol_orders', ezib.symbol_orders)
        ]
        
        for prop_name, prop_value in properties:
            count = len(prop_value) if prop_value else 0
            status = "✓" if prop_value else "✗"
            print(f"  ezib.{prop_name:<12}: {status} ({count} items)")
            
        print("\nNote: All properties auto-update after connection")
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        if ezib.connected:
            ezib.disconnect()
            print("Disconnected")


if __name__ == "__main__":
    asyncio.run(main())