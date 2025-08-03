#!/usr/bin/env python3
"""
Combo orders (spread trading) example for ezib_async.

Demonstrates:
- Creating option contracts for spreads
- Building combo legs and contracts
- Placing spread orders (bull call spread)

WARNING: This places real orders! Use paper trading account.
Requires options trading permissions and market data.
"""

import asyncio
from ezib_async import ezIBAsync


async def main():
    """Combo orders example - Bull Call Spread."""
    ezib = ezIBAsync()
    
    try:
        # Connect to IB
        print("Connecting to IB...")
        await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
        
        if not ezib.connected:
            print("Failed to connect")
            return
            
        print("Connected! Creating option contracts...")
        
        # Create option contracts for bull call spread
        symbol = "AAPL"
        expiry = "20251219"
        
        # Bull Call Spread: Buy lower strike, Sell higher strike
        buy_call = await ezib.createOptionContract(symbol, expiry=expiry, strike=200.0, otype="C")
        sell_call = await ezib.createOptionContract(symbol, expiry=expiry, strike=210.0, otype="C")
        
        print(f"Created options: {buy_call.symbol}, {sell_call.symbol}")
        
        # Get market data for pricing
        contracts = [buy_call, sell_call]
        await ezib.requestMarketData(contracts)
        await asyncio.sleep(5)
        
        # Display option prices
        print(f"\n=== OPTION PRICES ===")
        for contract in contracts:
            if contract.symbol in ezib.marketData:
                data = ezib.marketData[contract.symbol]
                print(f"{contract.strike}C: Bid={data.get('bid')} Ask={data.get('ask')}")
        
        # Check if combo methods exist
        if hasattr(ezib, 'createComboContract') and hasattr(ezib, 'createComboLeg'):
            print("\n=== COMBO ORDER ===")
            
            # Create combo legs
            leg1 = ezib.createComboLeg(buy_call, "BUY", ratio=1)
            leg2 = ezib.createComboLeg(sell_call, "SELL", ratio=1)
            
            # Build combo contract
            combo_contract = ezib.createComboContract(symbol, [leg1, leg2])
            
            # Create and place combo order
            combo_order = ezib.createOrder(quantity=1, price=1.00)  # Debit spread
            combo_trade = ezib.placeOrder(combo_contract, combo_order)
            
            if combo_trade:
                print(f"Combo order placed: {combo_trade.order.orderId}")
            
        else:
            print("\n=== MANUAL SPREAD ORDER ===")
            print("Combo methods not available, placing individual orders...")
            
            # Manual spread: place individual leg orders
            buy_order = ezib.createOrder(quantity=1, orderType="MKT")
            sell_order = ezib.createOrder(quantity=1, orderType="MKT")
            
            buy_trade = ezib.placeOrder(buy_call, buy_order)
            sell_trade = ezib.placeOrder(sell_call, sell_order)
            
            print(f"Buy leg: {buy_trade.order.orderId if buy_trade else 'Failed'}")
            print(f"Sell leg: {sell_trade.order.orderId if sell_trade else 'Failed'}")
        
        # Monitor orders
        await asyncio.sleep(5)
        print(f"\n=== ORDER STATUS ===")
        if ezib.orders:
            for order_id, order_info in ezib.orders.items():
                print(f"Order {order_id}: {order_info}")
        
        ezib.cancelMarketData(contracts)
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        if ezib.connected:
            ezib.disconnect()
            print("Disconnected")


if __name__ == "__main__":
    print("WARNING: This example places real combo/spread orders!")
    print("Requires options permissions and market data subscriptions.")
    print("Uncomment the line below to run:")
    # asyncio.run(main())