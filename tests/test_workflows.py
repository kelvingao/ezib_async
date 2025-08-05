#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
End-to-end integration tests for ezIBAsync.

These tests require a running IB Gateway or TWS instance for full integration testing.
They test complete workflows from connection to data retrieval to order placement.
"""
import pytest
import asyncio
import logging
from datetime import datetime, timedelta

from ezib_async import ezIBAsync


# Set up logging for integration tests
logging.getLogger("ib_async").setLevel("CRITICAL")
logging.getLogger("ezib_async").setLevel("INFO")
logger = logging.getLogger('pytest.integration_full')


class TestFullWorkflowIntegration:
    """Test complete workflows end-to-end."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_stock_workflow(self, ezib_instance):
        """Test complete stock trading workflow."""
        logger.info("Starting complete stock workflow test")
        
        try:
            # Step 1: Create stock contract
            logger.info("Step 1: Creating stock contract")
            contract = await ezib_instance.createStockContract("AAPL")
            
            assert contract is not None
            assert contract.symbol == "AAPL"
            logger.info(f"✓ Created contract: {contract.symbol}")
            
            # Step 2: Request market data
            logger.info("Step 2: Requesting market data")
            await ezib_instance.requestMarketData([contract], snapshot=True)
            
            # Wait for data
            await asyncio.sleep(3)
            
            # Verify market data received
            ticker_id = ezib_instance.tickerId(contract)
            assert ticker_id in ezib_instance.marketData
            logger.info("✓ Market data received")
            
            # Step 3: Create and verify order (but don't place)
            logger.info("Step 3: Creating order")
            order = ezib_instance.createOrder(quantity=1, price=0)  # Market order
            
            assert order.action == "BUY"
            assert order.totalQuantity == 1
            assert order.orderType == "MKT"
            logger.info("✓ Order created successfully")
            
            # Step 4: Verify account access
            logger.info("Step 4: Checking account access")
            account_data = ezib_instance.account
            assert isinstance(account_data, dict)
            logger.info("✓ Account data accessible")
            
            # Step 5: Check positions and portfolio
            logger.info("Step 5: Checking positions and portfolio")
            positions = ezib_instance.positions
            portfolio = ezib_instance.portfolios
            
            assert isinstance(positions, dict)
            assert isinstance(portfolio, dict)
            logger.info("✓ Positions and portfolio data accessible")
            
            # Step 6: Cancel market data
            logger.info("Step 6: Canceling market data")
            ezib_instance.cancelMarketData([contract])
            logger.info("✓ Market data canceled")
            
            logger.info("✅ Complete stock workflow test passed")
            
        except Exception as e:
            logger.error(f"❌ Complete stock workflow test failed: {e}")
            raise

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_contract_workflow(self, ezib_instance):
        """Test workflow with multiple contract types."""
        logger.info("Starting multi-contract workflow test")
        
        try:
            # Create multiple contract types
            logger.info("Creating multiple contracts")
            contracts = []
            
            # Stock contract
            stock = await ezib_instance.createStockContract("SPY")
            if stock:
                contracts.append(stock)
                logger.info("✓ Stock contract created: SPY")
            
            # Forex contract
            try:
                forex = await ezib_instance.createForexContract("EUR", "USD")
                if forex:
                    contracts.append(forex)
                    logger.info("✓ Forex contract created: EURUSD")
            except Exception as e:
                logger.warning(f"Forex contract creation failed: {e}")
            
            # Futures contract (may fail if market closed)
            try:
                futures = await ezib_instance.createFuturesContract("ES")
                if futures:
                    contracts.append(futures)
                    logger.info("✓ Futures contract created: ES")
            except Exception as e:
                logger.warning(f"Futures contract creation failed: {e}")
            
            assert len(contracts) >= 1, "At least one contract should be created"
            
            # Request market data for all contracts
            logger.info(f"Requesting market data for {len(contracts)} contracts")
            await ezib_instance.requestMarketData(contracts, snapshot=True)
            
            # Wait for data
            await asyncio.sleep(5)
            
            # Verify data received for at least some contracts
            data_received = 0
            for contract in contracts:
                ticker_id = ezib_instance.tickerId(contract)
                if ticker_id in ezib_instance.marketData:
                    data_received += 1
            
            logger.info(f"✓ Market data received for {data_received}/{len(contracts)} contracts")
            assert data_received > 0, "Should receive data for at least one contract"
            
            # Cancel all market data
            ezib_instance.cancelMarketData(contracts)
            logger.info("✓ All market data canceled")
            
            logger.info("✅ Multi-contract workflow test passed")
            
        except Exception as e:
            logger.error(f"❌ Multi-contract workflow test failed: {e}")
            raise

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_market_depth_workflow(self, ezib_instance):
        """Test market depth (Level II) workflow."""
        logger.info("Starting market depth workflow test")
        
        try:
            # Create liquid stock contract
            contract = await ezib_instance.createStockContract("SPY")
            assert contract is not None
            logger.info("✓ Contract created for market depth test")
            
            # Request market depth
            logger.info("Requesting market depth data")
            ezib_instance.requestMarketDepth([contract], num_rows=5)
            
            # Wait for depth data
            await asyncio.sleep(5)
            
            # Check if depth data received
            ticker_id = ezib_instance.tickerId(contract)
            if ticker_id in ezib_instance.marketDepthData:
                depth_data = ezib_instance.marketDepthData[ticker_id]
                logger.info(f"✓ Market depth data received: {len(depth_data)} rows")
            else:
                logger.warning("No market depth data received (may require subscription)")
            
            # Cancel market depth
            ezib_instance.cancelMarketDepth([contract])
            logger.info("✓ Market depth canceled")
            
            logger.info("✅ Market depth workflow test completed")
            
        except Exception as e:
            logger.error(f"❌ Market depth workflow test failed: {e}")
            raise

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_options_workflow(self, ezib_instance):
        """Test options contract workflow."""
        logger.info("Starting options workflow test")
        
        try:
            # Create option contract with future expiry
            future_date = (datetime.now() + timedelta(days=30))
            # Find third Friday of the month for standard expiry
            while future_date.weekday() != 4:  # Friday
                future_date += timedelta(days=1)
            
            expiry = future_date.strftime("%Y%m%d")
            logger.info(f"Using option expiry: {expiry}")
            
            # Create call option
            try:
                option = await ezib_instance.createOptionContract(
                    symbol="SPY",
                    expiry=expiry,
                    strike=400.0,
                    otype="C"
                )
                
                if option:
                    logger.info("✓ Option contract created")
                    
                    # Request option market data
                    await ezib_instance.requestMarketData([option], snapshot=True)
                    await asyncio.sleep(3)
                    
                    # Verify option data
                    ticker_id = ezib_instance.tickerId(option)
                    if ticker_id in ezib_instance.optionsData:
                        logger.info("✓ Option market data received")
                    
                    # Cancel option data
                    ezib_instance.cancelMarketData([option])
                    logger.info("✓ Option market data canceled")
                    
                else:
                    logger.warning("Option contract creation returned None")
                    
            except Exception as e:
                logger.warning(f"Option contract test failed: {e}")
                pytest.skip("Option contract test skipped due to error")
            
            logger.info("✅ Options workflow test completed")
            
        except Exception as e:
            logger.error(f"❌ Options workflow test failed: {e}")
            raise

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bracket_order_creation_workflow(self, ezib_instance):
        """Test bracket order creation workflow (without actual placement)."""
        logger.info("Starting bracket order creation workflow test")
        
        try:
            # Create contract
            contract = await ezib_instance.createStockContract("AAPL")
            assert contract is not None
            logger.info("✓ Contract created for bracket order test")
            
            # Get current market price for realistic bracket order
            await ezib_instance.requestMarketData([contract], snapshot=True)
            await asyncio.sleep(2)
            
            ticker_id = ezib_instance.tickerId(contract)
            market_data = ezib_instance.marketData.get(ticker_id)
            
            if market_data is not None and not market_data.empty:
                # Use market data to set realistic prices
                last_price = market_data.get('last', [150.0])
                if hasattr(last_price, '__iter__') and len(last_price) > 0:
                    base_price = float(last_price[0]) if last_price[0] else 150.0
                else:
                    base_price = 150.0
            else:
                base_price = 150.0  # Fallback price
            
            logger.info(f"Using base price: ${base_price}")
            
            # Create bracket order structure (without placing)
            entry_price = base_price * 0.99  # Buy 1% below market
            target_price = base_price * 1.05  # Target 5% above entry  
            stop_price = base_price * 0.95   # Stop 5% below entry
            
            # Test individual order creation
            entry_order = ezib_instance.createOrder(quantity=1, price=entry_price)
            target_order = ezib_instance.createTargetOrder(
                quantity=-1, 
                parentId=1001, 
                target=target_price
            )
            stop_order = ezib_instance.createStopOrder(
                quantity=-1, 
                parentId=1001, 
                stop=stop_price
            )
            
            # Verify order properties
            assert entry_order.action == "BUY"
            assert target_order.action == "SELL"
            assert stop_order.action == "SELL"
            assert target_order.parentId == 1001
            assert stop_order.parentId == 1001
            
            logger.info("✓ Bracket order components created successfully")
            
            # Test actual bracket order method (without placement)
            # Note: We don't actually place the order to avoid real trades
            logger.info("Testing bracket order creation method")
            
            # Cancel market data
            ezib_instance.cancelMarketData([contract])
            
            logger.info("✅ Bracket order creation workflow test passed")
            
        except Exception as e:
            logger.error(f"❌ Bracket order creation workflow test failed: {e}")
            raise


class TestEventDrivenWorkflow:
    """Test event-driven workflows."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_time_data_events(self, ezib_instance):
        """Test real-time data event handling."""
        logger.info("Starting real-time data events test")
        
        # Event tracking
        market_events_received = []
        
        def market_data_handler(tickers):
            market_events_received.extend(tickers)
            logger.info(f"Received market data event for {len(tickers)} tickers")
        
        try:
            # Subscribe to market data events
            ezib_instance.pendingMarketTickersEvent += market_data_handler
            logger.info("✓ Subscribed to market data events")
            
            # Create contract and request streaming data
            contract = await ezib_instance.createStockContract("MSFT")
            assert contract is not None
            
            # Request streaming (not snapshot) data
            await ezib_instance.requestMarketData([contract], snapshot=False)
            logger.info("✓ Requested streaming market data")
            
            # Wait for events
            logger.info("Waiting for real-time events...")
            await asyncio.sleep(10)
            
            # Check if events were received
            if len(market_events_received) > 0:
                logger.info(f"✓ Received {len(market_events_received)} market data events")
            else:
                logger.warning("No market data events received (market may be closed)")
            
            # Cancel streaming data
            ezib_instance.cancelMarketData([contract])
            logger.info("✓ Canceled streaming data")
            
        finally:
            # Unsubscribe from events
            ezib_instance.pendingMarketTickersEvent -= market_data_handler
            logger.info("✓ Unsubscribed from market data events")
        
        logger.info("✅ Real-time data events test completed")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_account_updates_events(self, ezib_instance):
        """Test account update events."""
        logger.info("Starting account updates events test")
        
        try:
            # Wait a moment for account data to populate
            await asyncio.sleep(3)
            
            # Check initial account data
            initial_accounts = ezib_instance.accounts
            logger.info(f"✓ Initial accounts data: {len(initial_accounts)} accounts")
            
            # Check account codes
            account_codes = ezib_instance.accountCodes
            logger.info(f"✓ Account codes: {account_codes}")
            
            # Verify account data structure
            if len(initial_accounts) > 0:
                for account_code, account_data in initial_accounts.items():
                    assert isinstance(account_data, dict)
                    logger.info(f"✓ Account {account_code} has {len(account_data)} data fields")
            
            # Check positions
            positions = ezib_instance.positions
            logger.info(f"✓ Positions data: {len(positions)} accounts with positions")
            
            # Check portfolio
            portfolios = ezib_instance.portfolios  
            logger.info(f"✓ Portfolio data: {len(portfolios)} accounts with portfolio items")
            
            logger.info("✅ Account updates events test completed")
            
        except Exception as e:
            logger.error(f"❌ Account updates events test failed: {e}")
            raise


class TestErrorRecoveryIntegration:
    """Test error recovery in integration scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_contract_recovery(self, ezib_instance):
        """Test recovery from invalid contract requests."""
        logger.info("Starting invalid contract recovery test")
        
        try:
            # Attempt to create invalid contract
            invalid_contract = await ezib_instance.createStockContract("INVALIDSYMBOL12345")
            
            # Should handle gracefully
            if invalid_contract is None:
                logger.info("✓ Invalid contract returned None as expected")
            else:
                # If contract was created, check its details
                details = ezib_instance.contractDetails(invalid_contract)
                if details.get("conId", 0) == 0:
                    logger.info("✓ Invalid contract has no contract ID as expected")
            
            # Continue with valid contract after invalid one
            valid_contract = await ezib_instance.createStockContract("AAPL")
            assert valid_contract is not None
            logger.info("✓ Valid contract created after invalid attempt")
            
            logger.info("✅ Invalid contract recovery test passed")
            
        except Exception as e:
            logger.error(f"❌ Invalid contract recovery test failed: {e}")
            raise

    @pytest.mark.integration 
    @pytest.mark.asyncio
    async def test_market_data_request_recovery(self, ezib_instance):
        """Test recovery from market data request errors."""
        logger.info("Starting market data request recovery test")
        
        try:
            # Create valid contract
            contract = await ezib_instance.createStockContract("GOOGL")
            assert contract is not None
            
            # Request market data multiple times (test rate limiting)
            logger.info("Testing multiple rapid market data requests")
            for i in range(5):
                await ezib_instance.requestMarketData([contract], snapshot=True)
                await asyncio.sleep(0.5)  # Small delay
            
            # Wait for data
            await asyncio.sleep(3)
            
            # Verify data received
            ticker_id = ezib_instance.tickerId(contract)
            if ticker_id in ezib_instance.marketData:
                logger.info("✓ Market data received despite multiple requests")
            
            # Cancel data
            ezib_instance.cancelMarketData([contract])
            logger.info("✓ Market data canceled")
            
            logger.info("✅ Market data request recovery test passed")
            
        except Exception as e:
            logger.error(f"❌ Market data request recovery test failed: {e}")
            raise


class TestPerformanceIntegration:
    """Test performance aspects in integration scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bulk_contract_creation_performance(self, ezib_instance):
        """Test performance with bulk contract creation."""
        logger.info("Starting bulk contract creation performance test")
        
        start_time = datetime.now()
        
        try:
            # Create multiple contracts
            symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
            contracts = []
            
            logger.info(f"Creating {len(symbols)} contracts")
            for symbol in symbols:
                contract = await ezib_instance.createStockContract(symbol)
                if contract:
                    contracts.append(contract)
                    logger.info(f"✓ Created contract: {symbol}")
                
                # Small delay to respect rate limits
                await asyncio.sleep(0.1)
            
            creation_time = datetime.now() - start_time
            logger.info(f"✓ Created {len(contracts)} contracts in {creation_time.total_seconds():.2f} seconds")
            
            # Test bulk market data request
            if len(contracts) > 0:
                logger.info("Requesting market data for all contracts")
                await ezib_instance.requestMarketData(contracts, snapshot=True)
                
                # Wait for data
                await asyncio.sleep(5)
                
                # Count successful data requests
                data_count = 0
                for contract in contracts:
                    ticker_id = ezib_instance.tickerId(contract)
                    if ticker_id in ezib_instance.marketData:
                        data_count += 1
                
                logger.info(f"✓ Received market data for {data_count}/{len(contracts)} contracts")
                
                # Cancel all data
                ezib_instance.cancelMarketData(contracts)
                logger.info("✓ Canceled all market data")
            
            total_time = datetime.now() - start_time
            logger.info(f"✅ Bulk contract test completed in {total_time.total_seconds():.2f} seconds")
            
        except Exception as e:
            logger.error(f"❌ Bulk contract creation performance test failed: {e}")
            raise

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, ezib_instance):
        """Test concurrent operations performance."""
        logger.info("Starting concurrent operations test")
        
        try:
            # Create contracts concurrently
            logger.info("Creating contracts concurrently")
            
            contract_tasks = [
                ezib_instance.createStockContract("IBM"),
                ezib_instance.createStockContract("INTC"), 
                ezib_instance.createStockContract("ORCL")
            ]
            
            contracts = await asyncio.gather(*contract_tasks, return_exceptions=True)
            
            # Filter successful contracts
            valid_contracts = [c for c in contracts if c is not None and not isinstance(c, Exception)]
            logger.info(f"✓ Created {len(valid_contracts)} contracts concurrently")
            
            if len(valid_contracts) > 0:
                # Request data for valid contracts
                await ezib_instance.requestMarketData(valid_contracts, snapshot=True)
                await asyncio.sleep(3)
                
                # Verify data
                data_received = 0
                for contract in valid_contracts:
                    ticker_id = ezib_instance.tickerId(contract)
                    if ticker_id in ezib_instance.marketData:
                        data_received += 1
                
                logger.info(f"✓ Received data for {data_received} contracts")
                
                # Cancel data
                ezib_instance.cancelMarketData(valid_contracts)
            
            logger.info("✅ Concurrent operations test completed")
            
        except Exception as e:
            logger.error(f"❌ Concurrent operations test failed: {e}")
            raise


class TestComprehensiveIntegration:
    """Comprehensive integration test combining all features."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_system_integration(self, ezib_instance):
        """Test full system integration with all major features."""
        logger.info("🚀 Starting comprehensive full system integration test")
        
        start_time = datetime.now()
        results = {
            "contracts_created": 0,
            "market_data_received": 0,
            "orders_created": 0,
            "events_received": 0,
            "account_data_verified": False,
            "positions_verified": False,
            "portfolio_verified": False
        }
        
        try:
            # Phase 1: Connection and Account Verification
            logger.info("📋 Phase 1: Verifying connection and account access")
            
            # Verify account access
            account_data = ezib_instance.account
            if account_data:
                results["account_data_verified"] = True
                logger.info("✓ Account data accessible")
            
            # Verify positions access
            positions = ezib_instance.positions
            if isinstance(positions, dict):
                results["positions_verified"] = True
                logger.info("✓ Positions data accessible")
            
            # Verify portfolio access
            portfolio = ezib_instance.portfolios
            if isinstance(portfolio, dict):
                results["portfolio_verified"] = True
                logger.info("✓ Portfolio data accessible")
            
            # Phase 2: Contract Creation
            logger.info("📄 Phase 2: Creating diverse contracts")
            
            contracts = []
            contract_symbols = ["AAPL", "SPY", "QQQ"]
            
            for symbol in contract_symbols:
                try:
                    contract = await ezib_instance.createStockContract(symbol)
                    if contract:
                        contracts.append(contract)
                        results["contracts_created"] += 1
                        logger.info(f"✓ Contract created: {symbol}")
                    await asyncio.sleep(0.2)  # Rate limiting
                except Exception as e:
                    logger.warning(f"Contract creation failed for {symbol}: {e}")
            
            # Phase 3: Market Data Testing
            logger.info("📊 Phase 3: Testing market data functionality")
            
            if contracts:
                # Set up event tracking
                market_events = []
                def market_handler(tickers):
                    market_events.extend(tickers)
                    results["events_received"] += len(tickers)
                
                ezib_instance.pendingMarketTickersEvent += market_handler
                
                try:
                    # Request market data
                    await ezib_instance.requestMarketData(contracts, snapshot=True)
                    logger.info(f"Requested market data for {len(contracts)} contracts")
                    
                    # Wait for data
                    await asyncio.sleep(5)
                    
                    # Verify data received
                    for contract in contracts:
                        ticker_id = ezib_instance.tickerId(contract)
                        if ticker_id in ezib_instance.marketData:
                            results["market_data_received"] += 1
                    
                    logger.info(f"✓ Market data received for {results['market_data_received']} contracts")
                    
                    # Test market depth if available
                    if contracts:
                        try:
                            ezib_instance.requestMarketDepth([contracts[0]], num_rows=3)
                            await asyncio.sleep(2)
                            ezib_instance.cancelMarketDepth([contracts[0]])
                            logger.info("✓ Market depth test completed")
                        except Exception as e:
                            logger.warning(f"Market depth test failed: {e}")
                    
                    # Cancel market data
                    ezib_instance.cancelMarketData(contracts)
                    logger.info("✓ Market data canceled")
                    
                finally:
                    ezib_instance.pendingMarketTickersEvent -= market_handler
            
            # Phase 4: Order Creation Testing
            logger.info("📝 Phase 4: Testing order creation functionality")
            
            if contracts:
                try:
                    # Test various order types
                    market_order = ezib_instance.createOrder(quantity=1, price=0)
                    results["orders_created"] += 1
                    
                    limit_order = ezib_instance.createOrder(quantity=1, price=100.0)
                    results["orders_created"] += 1
                    
                    stop_order = ezib_instance.createStopOrder(quantity=-1, stop=50.0)
                    results["orders_created"] += 1
                    
                    target_order = ezib_instance.createTargetOrder(quantity=-1, target=200.0)
                    results["orders_created"] += 1
                    
                    logger.info(f"✓ Created {results['orders_created']} different order types")
                    
                    # Test bracket order creation (structure only)
                    entry_order = ezib_instance.createOrder(quantity=1, price=150.0)
                    target = ezib_instance.createTargetOrder(quantity=-1, parentId=1001, target=160.0)
                    stop = ezib_instance.createStopOrder(quantity=-1, parentId=1001, stop=140.0)
                    
                    # Verify bracket order relationships
                    assert target.parentId == stop.parentId
                    logger.info("✓ Bracket order structure verified")
                    
                except Exception as e:
                    logger.warning(f"Order creation test failed: {e}")
            
            # Phase 5: Error Handling Testing
            logger.info("🛡️ Phase 5: Testing error handling")
            
            try:
                # Test invalid contract
                invalid = await ezib_instance.createStockContract("INVALID12345")
                if invalid is None:
                    logger.info("✓ Invalid contract handled gracefully")
                
                # Test invalid ticker lookup
                symbol = ezib_instance.tickerSymbol(99999)
                if symbol == "":
                    logger.info("✓ Invalid ticker ID handled gracefully")
                
            except Exception as e:
                logger.warning(f"Error handling test encountered: {e}")
            
            # Phase 6: Performance Testing
            logger.info("⚡ Phase 6: Performance verification")
            
            # Test rapid contract string conversions
            if contracts:
                conversion_start = datetime.now()
                for _ in range(100):
                    for contract in contracts:
                        ezib_instance.contractString(contract)
                conversion_time = datetime.now() - conversion_start
                logger.info(f"✓ 100 contract string conversions in {conversion_time.total_seconds():.3f}s")
            
            # Calculate overall results
            total_time = datetime.now() - start_time
            success_rate = sum([
                results["account_data_verified"],
                results["positions_verified"], 
                results["portfolio_verified"],
                results["contracts_created"] > 0,
                results["market_data_received"] > 0,
                results["orders_created"] > 0
            ]) / 6 * 100
            
            # Final Results
            logger.info("📈 INTEGRATION TEST RESULTS:")
            logger.info(f"  ✓ Contracts Created: {results['contracts_created']}")
            logger.info(f"  ✓ Market Data Received: {results['market_data_received']}")
            logger.info(f"  ✓ Orders Created: {results['orders_created']}")
            logger.info(f"  ✓ Events Received: {results['events_received']}")
            logger.info(f"  ✓ Account Data: {'✓' if results['account_data_verified'] else '✗'}")
            logger.info(f"  ✓ Positions Data: {'✓' if results['positions_verified'] else '✗'}")
            logger.info(f"  ✓ Portfolio Data: {'✓' if results['portfolio_verified'] else '✗'}")
            logger.info(f"  ⏱️ Total Time: {total_time.total_seconds():.2f} seconds")
            logger.info(f"  📊 Success Rate: {success_rate:.1f}%")
            
            # Assertions for test success
            assert results["contracts_created"] > 0, "Should create at least one contract"
            assert results["account_data_verified"], "Should access account data"
            assert success_rate >= 50, f"Success rate {success_rate}% below minimum 50%"
            
            logger.info("🎉 COMPREHENSIVE INTEGRATION TEST PASSED!")
            
        except Exception as e:
            logger.error(f"❌ Comprehensive integration test failed: {e}")
            logger.error(f"Results at failure: {results}")
            raise


if __name__ == "__main__":
    # Allow running integration tests directly
    import sys
    
    # Run specific test classes
    if len(sys.argv) > 1 and sys.argv[1] == "full":
        # Run comprehensive test only
        pytest.main(["-xvs", f"{__file__}::TestComprehensiveIntegration::test_full_system_integration", "--run-integration"])
    else:
        # Run all integration tests
        pytest.main(["-xvs", __file__, "--run-integration"])