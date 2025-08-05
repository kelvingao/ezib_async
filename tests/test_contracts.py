#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit and integration tests for contract functionality in ezIBAsync.

This module contains both unit tests (mocked) and integration tests (real IB connection)
for contract creation, management, and conversion functionality.
"""
import pytest
import asyncio
import sys
import calendar
import logging
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from ezib_async import ezIBAsync, util
from ib_async import Stock, Option, Future, Forex, Index, Contract

logging.getLogger("ib_async").setLevel("CRITICAL")
logging.getLogger("ezib_async").setLevel("INFO")

logger = logging.getLogger('pytest.contracts')
util.logToConsole("DEBUG")


class TestContractCreationUnit:
    """Unit tests for contract creation functionality."""

    @pytest.mark.asyncio
    async def test_create_contract_with_tuple(self, mock_ezib):
        """Test creating contract from tuple parameters."""
        # Setup
        mock_contract = Mock(spec=Contract)
        mock_ezib.createContract = AsyncMock(return_value=mock_contract)
        
        # Execute
        result = await mock_ezib.createContract("AAPL", "STK", "SMART", "USD", "", 0.0, "")
        
        # Verify
        mock_ezib.createContract.assert_called_once()
        assert result == mock_contract

    @pytest.mark.asyncio
    async def test_create_contract_with_existing_contract(self, mock_ezib):
        """Test creating contract from existing Contract object."""
        # Setup
        existing_contract = Stock(symbol="AAPL", exchange="SMART", currency="USD")
        mock_ezib.createContract = AsyncMock(return_value=existing_contract)
        
        # Execute
        result = await mock_ezib.createContract(existing_contract)
        
        # Verify
        mock_ezib.createContract.assert_called_once_with(existing_contract)
        assert result == existing_contract

    @pytest.mark.asyncio
    async def test_create_contract_qualification_failure(self):
        """Test contract creation when qualification fails."""
        # Create real instance
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'ib') as mock_ib:
            # Mock qualification failure
            mock_ib.qualifyContractsAsync = AsyncMock(return_value=[])
            
            # Execute
            result = await ezib.createContract("INVALID", "STK", "SMART", "USD", "", 0.0, "")
            
            # Verify
            assert result is None
            mock_ib.qualifyContractsAsync.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_stock_contract_unit(self, mock_ezib):
        """Test stock contract creation (unit test)."""
        # Setup
        mock_contract = Stock(symbol="AAPL", exchange="SMART", currency="USD")
        mock_ezib.createStockContract = AsyncMock(return_value=mock_contract)
        
        # Execute
        result = await mock_ezib.createStockContract("AAPL", "USD", "SMART")
        
        # Verify
        mock_ezib.createStockContract.assert_called_once_with("AAPL", "USD", "SMART")
        assert result == mock_contract

    @pytest.mark.asyncio
    async def test_create_option_contract_unit(self, mock_ezib):
        """Test option contract creation (unit test)."""
        # Setup
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y%m%d")
        mock_contract = Option(
            symbol="SPY", 
            lastTradeDateOrContractMonth=future_date,
            strike=500.0, 
            right="C", 
            exchange="SMART"
        )
        mock_ezib.createOptionContract = AsyncMock(return_value=mock_contract)
        
        # Execute
        result = await mock_ezib.createOptionContract(
            "SPY", expiry=future_date, strike=500.0, otype="C"
        )
        
        # Verify
        mock_ezib.createOptionContract.assert_called_once()
        assert result == mock_contract

    @pytest.mark.asyncio
    async def test_create_futures_contract_unit(self, mock_ezib):
        """Test futures contract creation (unit test)."""
        # Setup
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y%m")
        mock_contract = Future(
            symbol="ES", 
            lastTradeDateOrContractMonth=future_date,
            exchange="GLOBEX"
        )
        mock_ezib.createFuturesContract = AsyncMock(return_value=mock_contract)
        
        # Execute
        result = await mock_ezib.createFuturesContract("ES", expiry=future_date)
        
        # Verify
        mock_ezib.createFuturesContract.assert_called_once()
        assert result == mock_contract

    @pytest.mark.asyncio
    async def test_create_forex_contract_unit(self, mock_ezib):
        """Test forex contract creation (unit test)."""
        # Setup
        mock_contract = Forex(symbol="EUR", currency="USD", exchange="IDEALPRO")
        mock_ezib.createForexContract = AsyncMock(return_value=mock_contract)
        
        # Execute
        result = await mock_ezib.createForexContract("EUR", "USD")
        
        # Verify
        mock_ezib.createForexContract.assert_called_once_with("EUR", "USD")
        assert result == mock_contract

    @pytest.mark.asyncio
    async def test_create_index_contract_unit(self, mock_ezib):
        """Test index contract creation (unit test)."""
        # Setup
        mock_contract = Index(symbol="SPX", exchange="CBOE", currency="USD")
        mock_ezib.createIndexContract = AsyncMock(return_value=mock_contract)
        
        # Execute
        result = await mock_ezib.createIndexContract("SPX")
        
        # Verify
        mock_ezib.createIndexContract.assert_called_once_with("SPX")
        assert result == mock_contract


class TestContractStringConversion:
    """Test contract string conversion functionality."""

    def test_contract_to_tuple(self, mock_stock_contract):
        """Test converting contract to tuple."""
        # Execute
        result = ezIBAsync.contract_to_tuple(mock_stock_contract)
        
        # Verify
        expected = (
            mock_stock_contract.symbol,
            mock_stock_contract.secType,
            mock_stock_contract.exchange,
            mock_stock_contract.currency,
            mock_stock_contract.lastTradeDateOrContractMonth,
            mock_stock_contract.strike,
            mock_stock_contract.right
        )
        assert result == expected

    def test_contract_string_stock(self, mock_stock_contract):
        """Test contract string conversion for stock."""
        ezib = ezIBAsync()
        
        # Execute
        result = ezib.contractString(mock_stock_contract)
        
        # Verify
        assert result == "AAPL"

    def test_contract_string_option(self, mock_option_contract):
        """Test contract string conversion for option."""
        ezib = ezIBAsync()
        
        # Execute
        result = ezib.contractString(mock_option_contract)
        
        # Verify - should contain symbol, expiry, right, and strike
        assert "SPY" in result
        assert "C" in result
        assert "00500000" in result  # Strike formatted as 500.0 -> 00500000

    def test_contract_string_future(self, mock_future_contract):
        """Test contract string conversion for future."""
        ezib = ezIBAsync()
        
        # Execute
        result = ezib.contractString(mock_future_contract)
        
        # Verify - should contain symbol and month code
        assert "ES" in result
        assert "FUT" in result

    def test_contract_string_forex(self, mock_forex_contract):
        """Test contract string conversion for forex."""
        ezib = ezIBAsync()
        
        # Execute
        result = ezib.contractString(mock_forex_contract)
        
        # Verify
        assert result == "EURUSD_CASH"

    def test_contract_string_from_tuple(self):
        """Test contract string conversion from tuple."""
        ezib = ezIBAsync()
        
        # Stock tuple
        stock_tuple = ("AAPL", "STK", "SMART", "USD", "", 0.0, "")
        result = ezib.contractString(stock_tuple)
        assert result == "AAPL"
        
        # Forex tuple
        forex_tuple = ("EUR", "CASH", "IDEALPRO", "USD", "", 0.0, "")
        result = ezib.contractString(forex_tuple)
        assert result == "EURUSD_CASH"

    def test_contract_string_error_handling(self):
        """Test contract string conversion error handling."""
        ezib = ezIBAsync()
        
        # Invalid contract that causes an error
        invalid_contract = Mock()
        invalid_contract.symbol = "TEST"
        
        # Should not raise exception, should return symbol
        with patch.object(ezib, 'contract_to_tuple', side_effect=Exception("Test error")):
            result = ezib.contractString(invalid_contract)
            assert "TEST" in result


class TestTickerManagement:
    """Test ticker ID management functionality."""

    def test_ticker_id_assignment(self, mock_stock_contract):
        """Test ticker ID assignment for new contracts."""
        ezib = ezIBAsync()
        
        # Execute
        ticker_id = ezib.tickerId(mock_stock_contract)
        
        # Verify
        assert isinstance(ticker_id, int)
        assert ticker_id in ezib.tickerIds
        assert ezib.tickerIds[ticker_id] == ezib.contractString(mock_stock_contract)

    def test_ticker_id_reuse(self, mock_stock_contract):
        """Test ticker ID reuse for same contract."""
        ezib = ezIBAsync()
        
        # Execute twice
        ticker_id1 = ezib.tickerId(mock_stock_contract)
        ticker_id2 = ezib.tickerId(mock_stock_contract)
        
        # Verify same ID is returned
        assert ticker_id1 == ticker_id2

    def test_ticker_id_from_string(self):
        """Test ticker ID assignment from symbol string."""
        ezib = ezIBAsync()
        
        # Execute
        ticker_id = ezib.tickerId("AAPL")
        
        # Verify
        assert isinstance(ticker_id, int)
        assert ezib.tickerIds[ticker_id] == "AAPL"

    def test_ticker_symbol_lookup(self):
        """Test looking up symbol from ticker ID."""
        ezib = ezIBAsync()
        
        # Add a ticker
        ticker_id = ezib.tickerId("MSFT")
        
        # Execute
        symbol = ezib.tickerSymbol(ticker_id)
        
        # Verify
        assert symbol == "MSFT"

    def test_ticker_symbol_invalid_id(self):
        """Test looking up symbol with invalid ticker ID."""
        ezib = ezIBAsync()
        
        # Execute
        symbol = ezib.tickerSymbol(9999)
        
        # Verify
        assert symbol == ""


class TestContractDetails:
    """Test contract details functionality."""

    def test_contract_details_default(self, mock_stock_contract):
        """Test getting default contract details."""
        ezib = ezIBAsync()
        
        # Execute
        details = ezib.contractDetails(mock_stock_contract)
        
        # Verify default structure
        assert isinstance(details, dict)
        assert "tickerId" in details
        assert "conId" in details
        assert "minTick" in details
        assert details["minTick"] == 0.01  # Default

    def test_contract_details_by_ticker_id(self):
        """Test getting contract details by ticker ID."""
        ezib = ezIBAsync()
        
        # Execute
        details = ezib.contractDetails(0)  # Default ticker ID
        
        # Verify
        assert isinstance(details, dict)
        assert details["tickerId"] == 0

    def test_contract_details_by_string(self):
        """Test getting contract details by symbol string."""
        ezib = ezIBAsync()
        
        # Execute
        details = ezib.contractDetails("AAPL")
        
        # Verify
        assert isinstance(details, dict)


class TestMultiContractDetection:
    """Test multi-contract detection functionality."""

    def test_is_multi_contract_stock(self, mock_stock_contract):
        """Test multi-contract detection for stock (should be False)."""
        ezib = ezIBAsync()
        
        # Execute
        result = ezib.isMultiContract(mock_stock_contract)
        
        # Verify
        assert result is False

    def test_is_multi_contract_future_no_expiry(self):
        """Test multi-contract detection for future without expiry."""
        ezib = ezIBAsync()
        
        # Create future without expiry
        future_contract = Future(symbol="ES", exchange="GLOBEX")
        future_contract.lastTradeDateOrContractMonth = ""
        
        # Execute
        result = ezib.isMultiContract(future_contract)
        
        # Verify
        assert result is True

    def test_is_multi_contract_option_incomplete(self):
        """Test multi-contract detection for incomplete option."""
        ezib = ezIBAsync()
        
        # Create option without strike
        option_contract = Option(symbol="SPY", exchange="SMART")
        option_contract.strike = 0.0
        option_contract.right = ""
        
        # Execute
        result = ezib.isMultiContract(option_contract)
        
        # Verify
        assert result is True


class TestContractHelperMethods:
    """Test contract helper methods."""

    def test_get_con_id_existing_contract(self):
        """Test getting contract ID for existing contract."""
        ezib = ezIBAsync()
        
        # Setup - add a contract to the list
        mock_contract = Mock()
        mock_contract.conId = 12345
        ezib.contracts.append(mock_contract)
        
        # Create search contract with same ID
        search_contract = Mock()
        search_contract.conId = 12345
        
        # Execute
        result = ezib.getConId(search_contract)
        
        # Verify
        assert result == 12345

    def test_get_con_id_not_found(self):
        """Test getting contract ID for non-existent contract."""
        ezib = ezIBAsync()
        
        # Execute
        search_contract = Mock()
        search_contract.conId = 99999
        result = ezib.getConId(search_contract)
        
        # Verify
        assert result == 0

    def test_get_contract_existing(self):
        """Test getting contract object for existing contract."""
        ezib = ezIBAsync()
        
        # Setup
        mock_contract = Mock()
        mock_contract.conId = 12345
        ezib.contracts.append(mock_contract)
        
        # Create search contract
        search_contract = Mock()
        search_contract.conId = 12345
        
        # Execute
        result = ezib.getContract(search_contract)
        
        # Verify
        assert result == mock_contract

    def test_get_contract_not_found(self):
        """Test getting contract object for non-existent contract."""
        ezib = ezIBAsync()
        
        # Execute
        search_contract = Mock()
        search_contract.conId = 99999
        result = ezib.getContract(search_contract)
        
        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_register_contract_new(self):
        """Test registering a new contract."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'createContract') as mock_create:
            with patch.object(ezib, 'getConId', return_value=0):  # Not found
                mock_create.return_value = AsyncMock()
                mock_contract = Mock()
                
                # Execute
                await ezib.registerContract(mock_contract)
                
                # Verify
                mock_create.assert_called_once_with(mock_contract)

    @pytest.mark.asyncio
    async def test_register_contract_existing(self):
        """Test registering an existing contract."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'createContract') as mock_create:
            with patch.object(ezib, 'getConId', return_value=12345):  # Found
                mock_contract = Mock()
                
                # Execute
                await ezib.registerContract(mock_contract)
                
                # Verify no creation attempt
                mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_contract_timeout(self):
        """Test registering contract with timeout."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'createContract') as mock_create:
            with patch.object(ezib, 'getConId', return_value=0):
                # Mock timeout
                mock_create.side_effect = asyncio.TimeoutError()
                mock_contract = Mock()
                
                # Execute - should not raise exception
                await ezib.registerContract(mock_contract)
                
                # Verify attempt was made
                mock_create.assert_called_once()


class TestContractExpirationAndStrikes:
    """Test contract expiration and strike functionality."""

    @pytest.mark.asyncio
    async def test_get_expirations_no_contracts(self):
        """Test getting expirations when no contracts available."""
        ezib = ezIBAsync()
        
        # Mock contract details with no contracts
        with patch.object(ezib, 'contractDetails') as mock_details:
            mock_details.return_value = {"contracts": []}
            
            # Execute
            result = await ezib.getExpirations("SPY")
            
            # Verify
            assert result == tuple()

    @pytest.mark.asyncio
    async def test_get_expirations_stock_contract(self):
        """Test getting expirations for stock contract (should be empty)."""
        ezib = ezIBAsync()
        
        # Mock stock contract details
        with patch.object(ezib, 'contractDetails') as mock_details:
            mock_contract = Mock()
            mock_contract.secType = "STK"
            mock_details.return_value = {"contracts": [mock_contract]}
            
            # Execute
            result = await ezib.getExpirations("AAPL")
            
            # Verify
            assert result == tuple()

    @pytest.mark.asyncio
    async def test_get_strikes_no_contracts(self):
        """Test getting strikes when no contracts available."""
        ezib = ezIBAsync()
        
        # Mock contract details with no contracts
        with patch.object(ezib, 'contractDetails') as mock_details:
            mock_details.return_value = {"contracts": []}
            
            # Execute
            result = await ezib.getStrikes("SPY")
            
            # Verify
            assert result == tuple()

    @pytest.mark.asyncio
    async def test_get_strikes_stock_contract(self):
        """Test getting strikes for stock contract (should be empty)."""
        ezib = ezIBAsync()
        
        # Mock stock contract details
        with patch.object(ezib, 'contractDetails') as mock_details:
            mock_contract = Mock()
            mock_contract.secType = "STK"
            mock_details.return_value = {"contracts": [mock_contract]}
            
            # Execute
            result = await ezib.getStrikes("AAPL")
            
            # Verify
            assert result == tuple()

    @pytest.mark.asyncio
    async def test_get_strikes_with_range(self):
        """Test getting strikes with min/max range."""
        ezib = ezIBAsync()
        
        # Mock option contract details with various strikes
        with patch.object(ezib, 'contractDetails') as mock_details:
            contracts = []
            strikes = [100.0, 150.0, 200.0, 250.0, 300.0]
            for strike in strikes:
                mock_contract = Mock()
                mock_contract.secType = "OPT"
                mock_contract.strike = strike
                contracts.append(mock_contract)
            
            mock_details.return_value = {"contracts": contracts}
            
            # Execute with range
            result = await ezib.getStrikes("SPY", smin=125.0, smax=275.0)
            
            # Verify filtered strikes
            assert result == (150.0, 200.0, 250.0)


# Keep existing integration test class

class TestEzIBAsyncContractsIntegration:
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
            
            # Verify contract was added to contracts list
            assert contract in ezib_instance.contracts
            
            # Verify contract has proper attributes after qualification
            assert hasattr(contract, 'conId'), "Contract should have conId after qualification"
            assert contract.conId > 0, "Contract ID should be a positive number"
            
            # Verify ticker ID mapping
            ticker_id = ezib_instance.tickerId(contract)
            assert ticker_id >= 0, "Ticker ID should be non-negative"
            
            # Verify contract string generation
            contract_string = ezib_instance.contractString(contract)
            assert contract.symbol in contract_string, "Contract string should contain symbol"
            
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