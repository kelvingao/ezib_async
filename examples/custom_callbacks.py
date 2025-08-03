#!/usr/bin/env python3
"""
Custom callbacks example for ezib_async.

Demonstrates:
- Setting up custom event handlers
- Monitoring order status changes
- Handling market data updates
- Price alerts and trading logic

WARNING: This places a test order for callback testing!
"""

import asyncio
from ezib_async import ezIBAsync


class SimpleBot:
    """Simple trading bot with event handlers."""
    
    def __init__(self, ezib):
        self.ezib = ezib
        self.filled_orders = []
        
    def setup_events(self):
        """Set up event handlers using ib_async."""
        try:
            ib = self.ezib.ib
            
            # Order status events
            if hasattr(ib, 'orderStatusEvent'):
                ib.orderStatusEvent += self.on_order_status
                print("Connected to order status events")
                
            # Ticker events
            if hasattr(ib, 'pendingTickersEvent'):
                ib.pendingTickersEvent += self.on_ticker_update
                print("Connected to ticker events")
                
        except Exception as e:
            print(f"Error setting up events: {e}")
    
    def on_order_status(self, trade):
        """Handle order status changes."""
        order_id = trade.order.orderId
        status = trade.orderStatus.status
        filled = trade.orderStatus.filled
        
        print(f"📊 Order {order_id}: {status} (Filled: {filled})")
        
        if status == "Filled" and order_id not in self.filled_orders:
            self.filled_orders.append(order_id)
            print(f"🎯 ORDER FILLED! Order ID: {order_id}")
    
    def on_ticker_update(self, tickers):
        """Handle market data updates."""
        for ticker in tickers:
            if ticker.last and ticker.last > 0:
                symbol = ticker.contract.symbol
                price = ticker.last
                print(f"📈 {symbol}: ${price}")
                
                # Example price alert
                if symbol == "AAPL" and price > 200:
                    print(f"🔔 PRICE ALERT: {symbol} above $200!")


async def main():
    """Custom callbacks example."""
    ezib = ezIBAsync()
    
    try:
        # Connect to IB
        print("Connecting to IB...")
        await ezib.connectAsync(ibhost='127.0.0.1', ibport=4001, ibclient=0)
        
        if not ezib.connected:
            print("Failed to connect")
            return
            
        print("Connected! Setting up bot...")
        
        # Create trading bot
        bot = SimpleBot(ezib)
        bot.setup_events()
        
        # Create contract and request market data
        contract = await ezib.createStockContract("AAPL")
        await ezib.requestMarketData([contract])
        
        # Place a test limit order (unlikely to fill immediately)
        current_price = None
        await asyncio.sleep(3)
        
        if contract.symbol in ezib.marketData:
            data = ezib.marketData[contract.symbol]
            current_price = data.get('last') or data.get('bid')
            
        if current_price:
            limit_price = round(current_price * 0.95, 2)  # Well below market
            print(f"Placing test limit order at ${limit_price}")
            
            order = ezib.createOrder(quantity=1, price=limit_price)
            trade = ezib.placeOrder(contract, order)
            
            if trade:
                print(f"Test order placed: {trade.order.orderId}")
        
        # Monitor events
        print("Monitoring events for 30 seconds...")
        await asyncio.sleep(30)
        
        print(f"\n=== SUMMARY ===")
        print(f"Filled orders: {bot.filled_orders}")
        print("Event monitoring completed")
        
        ezib.cancelMarketData([contract])
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        if ezib.connected:
            ezib.disconnect()
            print("Disconnected")


if __name__ == "__main__":
    print("WARNING: This example places a test order for callback demonstration!")
    print("Uncomment the line below to run:")
    # asyncio.run(main())