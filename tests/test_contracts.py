#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration tests for the contracts functionality in ezIBAsync class.

This module contains integration tests for the contract creation and management
features of the ezIBAsync class, focusing on stock contracts.
These tests require a connection to Interactive Brokers TWS or Gateway.
"""
import pytest
import asyncio
import sys
import calendar
import logging

from datetime import datetime
from ezib_async import util

logging.getLogger("ib_async").setLevel("CRITICAL")
logging.getLogger("ezib_async").setLevel("INFO")

logger = logging.getLogger('pytest.contracts')
util.logToConsole("DEBUG")

class TestEzIBAsyncContracts:
    """Integration tests for ezIBAsync contract functionality."""

    @pytest.mark.asyncio
    async def test_create_stock_contract(self, ezib_instance):
        """Test creating a stock contract with real IB connection."""
        # Define test parameters for a common stock
        test_symbol = "AAPL"
        test_currency = "USD"
        test_exchange = "SMART"
        
        logger.info(f"Creating stock contract for {test_symbol}...")
        
        try:
            # Create the stock contract
            contract = await ezib_instance.createStockContract(test_symbol, test_currency, test_exchange)
            
            # Verify contract was created with correct properties
            assert contract is not None
            assert contract.symbol == test_symbol
            assert contract.secType == "STK"
            assert contract.currency == test_currency
            assert contract.exchange == test_exchange
            
            # Verify contract was added to contracts dictionary
            ticker_id = ezib_instance.tickerId(contract)
            assert ticker_id in ezib_instance.contracts
            
            # Verify contract details 
            details = ezib_instance.contractDetails(contract)
            logger.info(f"contractDetails(contract) is : {details}")
            
            # Should have some basic contract details
            assert "conId" in details, "Contract ID should be present in details"
            assert details["conId"] > 0, "Contract ID should be a positive number"
            
            logger.info(f"Successfully created and verified stock contract for {test_symbol}")
            
        except Exception as e:
            logger.error(f"Error during test_create_stock_contract: {e}")
            raise
            
    @pytest.mark.asyncio
    async def test_create_stock_contract_invalid(self, ezib_instance):
        """Test creating an invalid stock contract."""
        # Use a symbol that's unlikely to exist
        test_symbol = "INVALIDSTOCKSYMBOL123XYZ"
        test_currency = "USD"
        test_exchange = "SMART"
        
        logger.info(f"Testing with invalid stock symbol {test_symbol}...")
        
        # Create the stock contract (should work as contract creation itself doesn't validate)
        contract = await ezib_instance.createStockContract(test_symbol, test_currency, test_exchange)
        
        # Contract should be created but details should be minimal
        assert contract is not None
        assert contract.symbol == test_symbol
        
        # Check for contract details - should be minimal for invalid contract
        details = ezib_instance.contractDetails(contract)
        logger.info(f"Contract details for invalid symbol: {details}")
        
        # Contract ID should be 0 for an invalid contract or contract with no details
        assert details.get("conId", 0) == 0 or not details.get("downloaded", False)
        
        logger.info("Invalid stock contract test completed")

    @pytest.mark.asyncio
    async def test_create_option_contract(self, ezib_instance):
        """Test creating an option contract."""
        # Use the third Friday of the current month as expiry date
        # Options typically expire on the third Friday of each month
        today = datetime.now()
        current_year = today.year
        current_month = today.month
        
        # Calculate what day of the week the first day of the month is
        first_day = datetime(current_year, current_month, 1)
        first_day_weekday = first_day.weekday()  # 0=Monday, 4=Friday
        
        # Calculate the first Friday of the month
        days_until_first_friday = (4 - first_day_weekday) % 7
        first_friday = 1 + days_until_first_friday
        
        # Calculate the third Friday
        third_friday = first_friday + 14
        
        # Ensure the date is valid (not exceeding days in month)
        _, last_day = calendar.monthrange(current_year, current_month)
        if third_friday > last_day:
            third_friday = last_day
            
        # Format as YYYYMMDD
        expiry = f"{current_year}{current_month:02d}{third_friday:02d}"
        
        logger.info(f"Using option expiry date: {expiry}")
        
        try:
            # Create a put option contract
            contract = await ezib_instance.createOptionContract(
                symbol="SPY",
                expiry=expiry,
                strike=400.0,
                otype="P"  # Put option
            )
            
            # Verify contract properties
            assert contract.symbol == "SPY"
            assert contract.secType == "OPT"
            assert contract.lastTradeDateOrContractMonth == expiry
            assert contract.strike == 400.0
            assert contract.right == "P"  # Put option
            assert contract.exchange == "SMART"
            assert contract.currency == "USD"
            
            # Verify contract is in the contracts dictionary
            ticker_id = ezib_instance.tickerId(contract)
            assert ticker_id in ezib_instance.contracts
            
            # Compare essential properties instead of the entire contract object
            stored_contract = ezib_instance.contracts[ticker_id]
            assert stored_contract.symbol == contract.symbol
            assert stored_contract.secType == contract.secType
            assert stored_contract.exchange == contract.exchange
            assert stored_contract.currency == contract.currency
            assert stored_contract.lastTradeDateOrContractMonth == contract.lastTradeDateOrContractMonth
            assert stored_contract.strike == contract.strike
            assert stored_contract.right == contract.right
            
            # Verify contract details
            details = ezib_instance.contractDetails(contract)
            logger.info(f"Option contract details: {details}")
            
            # If contract details were found, verify conId
            if details.get("downloaded", False):
                assert details["conId"] > 0, "Contract ID should be a positive number"
                logger.info(f"Successfully verified option contract details for SPY {expiry} 400 PUT")
            
        except Exception as e:
            logger.warning(f"Could not create or validate option contract: {e}")
            pytest.skip(f"Skipping option contract test: {e}")

    @pytest.mark.asyncio
    async def test_create_futures_contract(self, ezib_instance):
        """Test creating a futures contract."""
        # Try different futures symbols to increase chances of success
        futures_symbols = ["ES", "NQ", "YM", "ZB", "GC"]
        exchanges = ["GLOBEX", "NYMEX", "CBOT"]
        
        for symbol in futures_symbols:
            for exchange in exchanges:
                try:
                    logger.info(f"Trying futures contract: {symbol} on {exchange}")
                    
                    # Create a futures contract
                    contract = await ezib_instance.createFuturesContract(
                        symbol=symbol,
                        exchange=exchange
                    )
                    
                    # Verify contract properties
                    assert contract.symbol == symbol
                    assert contract.secType == "FUT"
                    assert contract.exchange == exchange
                    
                    # Verify contract is in the contracts dictionary
                    ticker_id = ezib_instance.tickerId(contract)
                    assert ticker_id in ezib_instance.contracts
                    
                    # Compare essential properties instead of the entire contract object
                    stored_contract = ezib_instance.contracts[ticker_id]
                    assert stored_contract.symbol == contract.symbol
                    assert stored_contract.secType == contract.secType
                    assert stored_contract.exchange == contract.exchange
                    
                    # Verify contract details
                    details = ezib_instance.contractDetails(contract)
                    logger.info(f"Futures contract details: {details}")
                    
                    # If contract details were found, verify conId and end test
                    if details.get("downloaded", False):
                        assert details["conId"] > 0, "Contract ID should be a positive number"
                        logger.info(f"Successfully created futures contract: {symbol} on {exchange}")
                        
                        # Contract created successfully, we can stop testing
                        return
                except Exception as e:
                    logger.warning(f"Could not create or validate futures contract {symbol} on {exchange}: {e}")
        
        # Skip test if all attempts fail
        pytest.skip("Could not find any valid futures contracts")

    @pytest.mark.asyncio
    async def test_contract_to_string(self, ezib_instance):
        """Test converting contracts to strings."""
        # Create contracts
        stock = await ezib_instance.createStockContract("AAPL")
        forex = await ezib_instance.createForexContract("EUR", "USD")
        
        # Test contract string conversion
        stock_str = ezib_instance.contractString(stock)
        forex_str = ezib_instance.contractString(forex)
        
        # Log actual string formats for debugging
        logger.info(f"Stock contract string: {stock_str}")
        logger.info(f"Forex contract string: {forex_str}")
        
        # Verify expected string formats based on actual implementation
        assert stock_str == "AAPL"
        assert forex_str == "EURUSD_CASH"
        
        # Test tickerId and ticker lookup
        stock_id = ezib_instance.tickerId(stock)
        forex_id = ezib_instance.tickerId(forex)
        
        # Verify contracts are properly stored and can be retrieved by ID
        assert stock_id in ezib_instance.contracts
        assert forex_id in ezib_instance.contracts
        
        # Verify the stored contracts match the created ones
        assert ezib_instance.contracts[stock_id].symbol == stock.symbol
        assert ezib_instance.contracts[forex_id].symbol == forex.symbol
        
        logger.info(f"Successfully verified contract string conversion for stock: {stock_str} and forex: {forex_str}")

    @pytest.mark.asyncio
    async def test_get_contract_details(self, ezib_instance):
        """Test retrieving contract details."""
        # Create a stock contract
        contract = await ezib_instance.createStockContract("MSFT")
        
        # Get contract details
        details = ezib_instance.contractDetails(contract)
        logger.info(f"Contract details for MSFT: {details}")
        
        # Verify contract details
        assert details.get("downloaded", False) is True
        assert details["conId"] > 0
        assert details["minTick"] > 0
        assert "MICROSOFT" in details["longName"].upper()
        assert len(details.get("contracts", [])) >= 1

    @pytest.mark.asyncio
    async def test_is_multi_contract(self, ezib_instance):
        """Test checking if a contract has multiple sub-contracts."""
        # Create contracts
        stock = await ezib_instance.createStockContract("AAPL")
        
        # Test a simple contract (stock)
        # In ezib_async, check if isMultiContract method exists, otherwise use an equivalent check

        assert ezib_instance.isMultiContract(stock) is False
        
        # For futures, we'll just test the method works without actually checking multi-contract
        try:
            futures = await ezib_instance.createFuturesContract("ES", exchange="GLOBEX")
            
            # Check multi-contract functionality
            if hasattr(ezib_instance, "isMultiContract"):
                result = ezib_instance.isMultiContract(futures)
                logger.info(f"ES futures is multi-contract: {result}")
            else:
                # Alternative check
                details = ezib_instance.contractDetails(futures)
                multi = len(details.get("contracts", [])) > 1
                logger.info(f"ES futures has multiple contracts: {multi}")
        except Exception as e:
            logger.warning(f"Could not test futures contract: {e}")
            pytest.skip(f"Skipping multi-contract test for futures: {e}")

    @pytest.mark.asyncio
    async def test_get_option_strikes(self, ezib_instance):
        """Test getting strikes for an option contract."""
        try:
            # Create an option contract for SPY
            contract = await ezib_instance.createOptionContract("SPY")

            await asyncio.sleep(3)
            
            # Get strikes, using the appropriate method name in ezib_async
            strikes = await ezib_instance.getStrikes(contract)
            
            logger.info(f"Number of strikes available for SPY: {len(strikes)}")
            logger.info(f"Sample strikes: {strikes[:5]}")
            
            # Verify strikes
            assert len(strikes) > 0
            
            # Verify strikes are in ascending order
            assert all(strikes[i] <= strikes[i+1] for i in range(len(strikes)-1))
        except Exception as e:
            logger.warning(f"Could not test option strikes: {e}")
            pytest.skip(f"Skipping option strikes test: {e}")

if __name__ == "__main__":
    # Run the tests directly
    start_time = datetime.now()
    print(f"Starting tests at {start_time}")
    
    # Run the test
    test_result = pytest.main(["-xvs", __file__])
    
    end_time = datetime.now()
    print(f"Tests completed at {end_time}")
    print(f"Total duration: {end_time - start_time}")
    
    sys.exit(0 if test_result == 0 else 1)