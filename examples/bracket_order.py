#!/usr/bin/env python3
"""
Bracket order example for ezib_async.

Demonstrates:
- Creating bracket orders (entry + profit target + stop loss)
- Manual bracket order implementation
- Risk management with stop/target orders

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
        
        current_price = None
        if contract.symbol in ezib.marketData:
            data = ezib.marketData[contract.symbol]
            current_price = data.get('last') or data.get('ask')
            print(f"Current AAPL price: ${current_price}")
        
        if not current_price:
            print("Could not get current price")
            return
        
        # Calculate bracket levels
        target_price = round(current_price * 1.02, 2)  # +2%
        stop_price = round(current_price * 0.99, 2)    # -1%
        
        print(f"\nBracket Order Setup:")
        print(f"  Entry: Market Order")
        print(f"  Target: ${target_price} (+2%)")
        print(f"  Stop: ${stop_price} (-1%)")
        
        # Check if createBracketOrder exists
        if hasattr(ezib, 'createBracketOrder'):
            print("\n=== BRACKET ORDER ===")
            bracket_order = await ezib.createBracketOrder(
                contract=contract,
                quantity=1,
                entry=0,  # Market order
                target=target_price,
                stop=stop_price
            )
            print(f"Bracket order created: {bracket_order}")
            
        else:
            print("\n=== MANUAL BRACKET ORDER ===")
            # Manual implementation: Entry order first
            entry_order = ezib.createOrder(quantity=1)
            entry_trade = ezib.placeOrder(contract, entry_order)
            
            if entry_trade:
                print(f"Entry order placed: {entry_trade.order.orderId}")
                await asyncio.sleep(2)
                
                # If filled, place target and stop orders
                if entry_trade.orderStatus.status == "Filled":
                    print("Entry filled! Placing target and stop orders...")
                    
                    # Target order
                    target_order = ezib.createOrder(quantity=-1, price=target_price, orderType="LMT")
                    target_trade = ezib.placeOrder(contract, target_order)
                    
                    # Stop order
                    stop_order = ezib.createOrder(quantity=-1, price=stop_price, orderType="STP", auxPrice=stop_price)
                    stop_trade = ezib.placeOrder(contract, stop_order)
                    
                    print(f"Target order: {target_trade.order.orderId if target_trade else 'Failed'}")
                    print(f"Stop order: {stop_trade.order.orderId if stop_trade else 'Failed'}")
        
        # Monitor orders
        await asyncio.sleep(5)
        print(f"\n=== ORDER STATUS ===")
        if ezib.orders:
            for order_id, order_info in ezib.orders.items():
                print(f"Order {order_id}: {order_info}")
        
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
    # asyncio.run(main())