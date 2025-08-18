#!/usr/bin/env python3
"""
Extended Hours Bracket order example for ezib_async.

Demonstrates:
- Creating bracket orders using ezib's built-in createBracketOrder method
- Extended hours trading (pre-market and after-hours)
- Entry order with automatic profit target and stop loss
- Risk management with OCA (One Cancels All) orders

WARNING: This places real orders! Use paper trading account.
"""

import asyncio
from ezib_async import ezIBAsync


async def main():
    """Bracket order example."""
    ezib = ezIBAsync()
    
    try:
        # Connect to IB
        print("Connecting to IB...")
        await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
        
        if not ezib.connected:
            print("Failed to connect")
            return
            
        print("Connected! Creating contract...")
        
        # Create contract and get market data
        contract = await ezib.createStockContract("AAPL")
        await ezib.requestMarketData([contract])
        await asyncio.sleep(3)
        
        # Get current price from market data
        ticker_id = ezib.tickerId(contract)
        market_data = ezib.marketData.get(ticker_id, {})
        current_price = market_data.get('last', [None])[-1] or market_data.get('ask', [None])[-1]
        
        if current_price:
            print(f"Current AAPL price: ${current_price}")
        else:
            print("Could not get current price")
            return
        
        # Calculate bracket levels
        target_price = round(current_price * 1.02, 2)  # +2%
        stop_price = round(current_price * 0.99, 2)    # -1%
        
        print(f"\nBracket Order Setup (Extended Hours):")
        print(f"  Entry: Market Order")
        print(f"  Target: ${target_price} (+2%)")
        print(f"  Stop: ${stop_price} (-1%)")
        print(f"  Extended Hours: Enabled")
        
        # Use ezib's built-in createBracketOrder method with extended hours
        print("\n=== BRACKET ORDER (Extended Hours) ===")
        bracket_result = ezib.createBracketOrder(
            contract=contract,
            quantity=1,
            entry=0,  # Market order
            target=target_price,
            stop=stop_price,
            rth=True  # Enable extended hours trading
        )
        print(f"Bracket order created:")
        print(f"  Entry Order ID: {bracket_result['entryOrderId']}")
        print(f"  Target Order ID: {bracket_result['targetOrderId']}")
        print(f"  Stop Order ID: {bracket_result['stopOrderId']}")
        print(f"  OCA Group: {bracket_result['group']}")
        
        # Monitor orders briefly
        await asyncio.sleep(5)
        print(f"\n=== ORDER STATUS ===")
        if ezib.orders:
            for order_info in ezib.orders.values():
                print(f"Order {order_info['id']}: {order_info['status']} - {order_info['symbol']}")
        else:
            print("No active orders found")
        
        # Cancel market data subscription
        ezib.cancelMarketData([contract])
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        if ezib.connected:
            ezib.disconnect()
            print("Disconnected")


if __name__ == "__main__":
    print("WARNING: This example places real bracket orders!")
    print("Uncomment the line below to run:")
    asyncio.run(main())