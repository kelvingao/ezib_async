#!/usr/bin/env python3
"""
Order submission example for ezib_async.

Demonstrates:
- Creating market and limit orders
- Placing orders and monitoring status
- Viewing positions after execution

WARNING: This places real orders! Use paper trading account.
"""

import asyncio
from ezib_async import ezIBAsync


async def main():
    """Order submission example."""
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
        
        # Get market data for limit order pricing
        await ezib.requestMarketData([contract])
        await asyncio.sleep(3)
        
        current_price = None
        if contract.symbol in ezib.marketData:
            data = ezib.marketData[contract.symbol]
            current_price = data.get('last') or data.get('bid')
            print(f"Current price: ${current_price}")
        
        # Example 1: Market Order
        print("\n=== MARKET ORDER ===")
        market_order = ezib.createOrder(quantity=1)
        trade = ezib.placeOrder(contract, market_order)
        
        if trade:
            print(f"Market order placed. Order ID: {trade.order.orderId}")
            await asyncio.sleep(2)
            print(f"Status: {trade.orderStatus.status}")
        
        # Example 2: Limit Order (if we have current price)
        if current_price:
            print("\n=== LIMIT ORDER ===")
            limit_price = round(current_price * 0.99, 2)
            limit_order = ezib.createOrder(quantity=1, price=limit_price)
            limit_trade = ezib.placeOrder(contract, limit_order)
            
            if limit_trade:
                print(f"Limit order placed at ${limit_price}. Order ID: {limit_trade.order.orderId}")
                await asyncio.sleep(2)
                print(f"Status: {limit_trade.orderStatus.status}")
        
        # Show positions
        await asyncio.sleep(3)
        print(f"\n=== POSITIONS ===")
        if ezib.positions:
            for account, positions in ezib.positions.items():
                for symbol, pos in positions.items():
                    print(f"{symbol}: {pos}")
        else:
            print("No positions found")
            
        ezib.cancelMarketData([contract])
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        if ezib.connected:
            ezib.disconnect()
            print("Disconnected")


if __name__ == "__main__":
    print("WARNING: This example places real orders!")
    print("Uncomment the line below to run:")
    # asyncio.run(main())