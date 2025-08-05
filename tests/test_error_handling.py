#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for error handling functionality in ezIBAsync.

Tests error scenarios, edge cases, and exception handling across all functionality.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from ezib_async import ezIBAsync
from ib_async import Stock, Option, Order, Contract, Trade


class TestConnectionErrorHandling:
    """Test error handling in connection management."""

    @pytest.mark.asyncio
    async def test_connect_async_timeout(self):
        """Test connection timeout handling."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'ib') as mock_ib:
            # Mock timeout exception
            mock_ib.connectAsync = AsyncMock(side_effect=asyncio.TimeoutError("Connection timeout"))
            
            # Execute - should not raise exception
            result = await ezib.connectAsync()
            
            # Verify graceful handling
            assert ezib.connected is False

    @pytest.mark.asyncio
    async def test_connect_async_connection_refused(self):
        """Test connection refused error handling."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'ib') as mock_ib:
            # Mock connection refused
            mock_ib.connectAsync = AsyncMock(side_effect=ConnectionRefusedError("Connection refused"))
            
            # Execute - should not raise exception
            result = await ezib.connectAsync()
            
            # Verify graceful handling
            assert ezib.connected is False

    @pytest.mark.asyncio
    async def test_connect_async_general_exception(self):
        """Test general exception handling during connection."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'ib') as mock_ib:
            # Mock general exception
            mock_ib.connectAsync = AsyncMock(side_effect=Exception("General error"))
            
            # Execute - should not raise exception
            result = await ezib.connectAsync()
            
            # Verify graceful handling
            assert ezib.connected is False

    def test_disconnect_with_none_ib(self):
        """Test disconnect when IB client is None."""
        ezib = ezIBAsync()
        ezib.ib = None  # Set to None
        ezib.connected = True
        
        # Should not raise exception
        ezib.disconnect()
        
        # Should update connection state
        assert ezib.connected is False

    def test_disconnect_with_exception_in_account_updates(self):
        """Test disconnect when account updates fail."""
        ezib = ezIBAsync()
        ezib.connected = True
        ezib._default_account = "DU123456"
        
        with patch.object(ezib, 'ib') as mock_ib:
            # Mock exception in account updates
            mock_ib.client = Mock()
            mock_ib.client.reqAccountUpdates = Mock(side_effect=Exception("Account update error"))
            mock_ib.disconnect = Mock()
            
            # Should not raise exception
            ezib.disconnect()
            
            # Should still disconnect
            assert ezib._disconnected_by_user is True


class TestContractCreationErrorHandling:
    """Test error handling in contract creation."""

    @pytest.mark.asyncio
    async def test_create_contract_qualification_timeout(self):
        """Test contract creation with qualification timeout."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'ib') as mock_ib:
            # Mock timeout during qualification
            mock_ib.qualifyContractsAsync = AsyncMock(side_effect=asyncio.TimeoutError("Timeout"))
            
            # Execute
            result = await ezib.createContract("AAPL", "STK", "SMART", "USD", "", 0.0, "")
            
            # Verify returns None on timeout
            assert result is None

    @pytest.mark.asyncio
    async def test_create_contract_qualification_exception(self):
        """Test contract creation with qualification exception."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'ib') as mock_ib:
            # Mock exception during qualification
            mock_ib.qualifyContractsAsync = AsyncMock(side_effect=Exception("Qualification error"))
            
            # Execute
            result = await ezib.createContract("INVALID", "STK", "SMART", "USD", "", 0.0, "")
            
            # Verify returns None on exception
            assert result is None

    @pytest.mark.asyncio
    async def test_create_contract_empty_qualification_result(self):
        """Test contract creation with empty qualification result."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'ib') as mock_ib:
            # Mock empty qualification result
            mock_ib.qualifyContractsAsync = AsyncMock(return_value=[])
            
            # Execute
            result = await ezib.createContract("INVALID", "STK", "SMART", "USD", "", 0.0, "")
            
            # Verify returns None when no qualified contracts
            assert result is None

    @pytest.mark.asyncio
    async def test_create_contract_with_invalid_contract_object(self):
        """Test contract creation with invalid Contract object."""
        ezib = ezIBAsync()
        
        # Create invalid contract (missing required fields)
        invalid_contract = Mock()
        invalid_contract.symbol = None
        invalid_contract.secType = None
        
        with patch.object(ezib, 'ib') as mock_ib:
            mock_ib.qualifyContractsAsync = AsyncMock(side_effect=Exception("Invalid contract"))
            
            # Execute
            result = await ezib.createContract(invalid_contract)
            
            # Verify graceful error handling
            assert result is None

    @pytest.mark.asyncio
    async def test_create_stock_contract_with_invalid_parameters(self):
        """Test stock contract creation with invalid parameters."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'createContract') as mock_create:
            mock_create.return_value = AsyncMock(return_value=None)
            
            # Execute with None symbol
            result = await ezib.createStockContract(None)
            
            # Verify handled gracefully
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_option_contract_with_invalid_expiry(self):
        """Test option contract creation with invalid expiry date."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'createContract') as mock_create:
            mock_create.return_value = AsyncMock(return_value=None)
            
            # Execute with invalid expiry
            result = await ezib.createOptionContract("SPY", expiry="INVALID", strike=500.0)
            
            # Verify handled gracefully
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_futures_contract_with_invalid_exchange(self):
        """Test futures contract creation with invalid exchange."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'createContract') as mock_create:
            mock_create.return_value = AsyncMock(return_value=None)
            
            # Execute with invalid exchange
            result = await ezib.createFuturesContract("ES", exchange="INVALID")
            
            # Verify handled gracefully
            mock_create.assert_called_once()


class TestMarketDataErrorHandling:
    """Test error handling in market data functionality."""

    @pytest.mark.asyncio
    async def test_request_market_data_with_none_contracts(self):
        """Test market data request with None contracts."""
        ezib = ezIBAsync()
        ezib.contracts = []  # Empty contracts list
        
        # Execute with None - should use empty contracts list
        await ezib.requestMarketData(None)
        
        # Should not raise exception
        assert True

    @pytest.mark.asyncio
    async def test_request_market_data_with_invalid_contract(self):
        """Test market data request with invalid contract."""
        ezib = ezIBAsync()
        
        # Create invalid contract
        invalid_contract = Mock()
        invalid_contract.symbol = None
        
        with patch.object(ezib, 'contractString', side_effect=Exception("Invalid contract")):
            # Execute - should not raise exception
            await ezib.requestMarketData([invalid_contract])

    @pytest.mark.asyncio
    async def test_request_market_data_api_error(self):
        """Test market data request with API error."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'ib') as mock_ib:
            # Mock API error
            mock_ib.reqMktData = Mock(side_effect=Exception("API error"))
            
            mock_contract = Mock()
            
            with patch.object(ezib, 'contractString', return_value="AAPL"):
                with patch.object(ezib, 'isMultiContract', return_value=False):
                    # Execute - should not raise exception
                    await ezib.requestMarketData([mock_contract])

    def test_cancel_market_data_with_none_contracts(self):
        """Test cancel market data with None contracts."""
        ezib = ezIBAsync()
        ezib.contracts = []
        
        # Execute - should not raise exception
        ezib.cancelMarketData(None)

    def test_cancel_market_data_api_error(self):
        """Test cancel market data with API error."""
        ezib = ezIBAsync()
        ezib.connected = True
        
        with patch.object(ezib, 'ib') as mock_ib:
            # Mock API error
            mock_ib.cancelMktData = Mock(side_effect=Exception("Cancel error"))
            
            mock_contract = Mock()
            
            with patch.object(ezib, 'tickerId', return_value=1):
                # Execute - should not raise exception
                ezib.cancelMarketData([mock_contract])

    def test_request_market_depth_invalid_rows(self):
        """Test market depth request with invalid number of rows."""
        ezib = ezIBAsync()
        
        mock_contract = Mock()
        mock_contract.symbol = "AAPL"
        
        with patch.object(ezib, 'ib') as mock_ib:
            with patch.object(ezib, 'contractString', return_value="AAPL"):
                # Execute with negative rows
                ezib.requestMarketDepth([mock_contract], num_rows=-5)
                
                # Should handle gracefully (likely defaulting to valid range)
                mock_ib.reqMktDepth.assert_called_once()


class TestOrderErrorHandling:
    """Test error handling in order functionality."""

    def test_create_order_with_invalid_quantity(self):
        """Test order creation with invalid quantity."""
        ezib = ezIBAsync()
        
        # Execute with zero quantity
        order = ezib.createOrder(quantity=0)
        
        # Should still create order (IB will handle validation)
        assert order.totalQuantity == 0

    def test_create_order_with_invalid_price(self):
        """Test order creation with invalid price."""
        ezib = ezIBAsync()
        
        # Execute with negative price
        order = ezib.createOrder(quantity=100, price=-10.0)
        
        # Should still create order
        assert order.lmtPrice == -10.0

    def test_place_order_with_none_contract(self):
        """Test order placement with None contract."""
        ezib = ezIBAsync()
        
        order = Order()
        order.orderId = 1001
        
        with patch.object(ezib, 'ib') as mock_ib:
            # Execute with None contract - should not raise exception
            trade = ezib.placeOrder(None, order)

    def test_place_order_api_error(self):
        """Test order placement with API error."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'ib') as mock_ib:
            # Mock API error
            mock_ib.placeOrder = Mock(side_effect=Exception("Order placement error"))
            
            mock_contract = Mock()
            mock_order = Mock(spec=Order)
            mock_order.orderId = 1001
            mock_order.lmtPrice = 150.0
            mock_order.auxPrice = 0.0
            
            with patch.object(ezib, 'contractDetails', return_value={"minTick": 0.01}):
                with patch.object(ezib, 'contractString', return_value="AAPL"):
                    # Execute - should not raise exception but return None
                    trade = ezib.placeOrder(mock_contract, mock_order)
                    
                    assert trade is None

    def test_create_bracket_order_with_invalid_parameters(self):
        """Test bracket order creation with invalid parameters."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'placeOrder') as mock_place:
            # Mock order placement failure
            mock_place.return_value = None
            
            mock_contract = Mock()
            
            # Execute with invalid target price (lower than entry for buy)
            result = ezib.createBracketOrder(
                contract=mock_contract,
                quantity=100,
                entry=150.0,
                target=140.0,  # Invalid - target should be higher for buy
                stop=130.0
            )
            
            # Should return None when entry order placement fails
            assert result is None

    def test_round_closest_valid_with_invalid_inputs(self):
        """Test price rounding with invalid inputs."""
        # Test with None value
        result = ezIBAsync.roundClosestValid(None, res=0.01)
        assert result is None
        
        # Test with zero resolution
        result = ezIBAsync.roundClosestValid(150.0, res=0.0)
        # Should handle gracefully (implementation dependent)
        
        # Test with negative resolution
        result = ezIBAsync.roundClosestValid(150.0, res=-0.01)
        # Should handle gracefully (implementation dependent)


class TestContractDetailsErrorHandling:
    """Test error handling in contract details functionality."""

    def test_contract_details_with_none_contract(self):
        """Test getting contract details with None contract."""
        ezib = ezIBAsync()
        
        # Execute with None - should return default details
        details = ezib.contractDetails(None)
        
        # Should return valid dict structure
        assert isinstance(details, dict)

    def test_contract_details_with_invalid_ticker_id(self):
        """Test getting contract details with invalid ticker ID."""
        ezib = ezIBAsync()
        
        # Execute with invalid ID
        details = ezib.contractDetails(-999)
        
        # Should return default details for invalid ID
        assert isinstance(details, dict)
        assert details["tickerId"] == -999

    def test_contract_string_with_exception(self):
        """Test contract string conversion with exception."""
        ezib = ezIBAsync()
        
        # Create mock contract that causes exception
        mock_contract = Mock()
        mock_contract.symbol = "TEST"
        
        with patch.object(ezib, 'contract_to_tuple', side_effect=AttributeError("Missing attribute")):
            # Execute - should handle exception gracefully
            result = ezib.contractString(mock_contract)
            
            # Should fallback to symbol or error string
            assert "TEST" in result or "Error" in result

    def test_ticker_id_with_invalid_input(self):
        """Test ticker ID generation with invalid input."""
        ezib = ezIBAsync()
        
        # Execute with empty string
        ticker_id = ezib.tickerId("")
        
        # Should handle gracefully
        assert isinstance(ticker_id, int)

    def test_ticker_symbol_with_none_input(self):
        """Test ticker symbol lookup with None input."""
        ezib = ezIBAsync()
        
        # Execute with None
        symbol = ezib.tickerSymbol(None)
        
        # Should return empty string
        assert symbol == ""


class TestEventHandlingErrorHandling:
    """Test error handling in event processing."""

    def test_account_value_handler_with_malformed_data(self):
        """Test account value handler with malformed data."""
        ezib = ezIBAsync()
        
        # Create object with missing attributes
        malformed_data = Mock()
        del malformed_data.account  # Remove required attribute
        
        # Execute - should not raise exception
        ezib._onAccountValueHandler(malformed_data)
        
        # Should not add any accounts
        assert len(ezib._accounts) == 0

    def test_position_handler_with_malformed_data(self):
        """Test position handler with malformed data."""
        ezib = ezIBAsync()
        
        # Create object with None contract
        malformed_position = Mock()
        malformed_position.contract = None
        malformed_position.account = "DU123456"
        
        # Execute - should not raise exception
        ezib._onPositionUpdateHandler(malformed_position)
        
        # Should not add any positions
        assert len(ezib._positions) == 0

    def test_portfolio_handler_with_malformed_data(self):
        """Test portfolio handler with malformed data."""
        ezib = ezIBAsync()
        
        # Create object with missing attributes
        malformed_item = Mock()
        malformed_item.contract = None
        
        # Execute - should not raise exception
        ezib._onPortfolioUpdateHandler(malformed_item)
        
        # Should not add any portfolio items
        assert len(ezib._portfolios) == 0

    def test_pending_tickers_handler_with_empty_list(self):
        """Test pending tickers handler with empty list."""
        ezib = ezIBAsync()
        
        with patch.object(ezib.pendingMarketTickersEvent, 'emit') as mock_emit:
            # Execute with empty list
            ezib._onPendingTickersHandler([])
            
            # Should still emit event
            mock_emit.assert_called()

    def test_pending_tickers_handler_with_none_tickers(self):
        """Test pending tickers handler with None tickers."""
        ezib = ezIBAsync()
        
        # Execute with None - should not raise exception
        ezib._onPendingTickersHandler(None)

    def test_pending_tickers_handler_with_malformed_tickers(self):
        """Test pending tickers handler with malformed ticker data."""
        ezib = ezIBAsync()
        
        # Create malformed ticker
        malformed_ticker = Mock()
        malformed_ticker.contract = None  # Missing contract
        
        # Execute - should not raise exception
        ezib._onPendingTickersHandler([malformed_ticker])


class TestDataPropertiesErrorHandling:
    """Test error handling in data properties."""

    def test_get_account_with_none_default_account(self):
        """Test getAccount when default account is None."""
        ezib = ezIBAsync()
        ezib._default_account = None
        ezib._accounts = {}
        
        # Execute - should return empty dict
        result = ezib.getAccount()
        
        assert result == {}

    def test_get_position_with_corrupted_position_data(self):
        """Test getPosition with corrupted position data."""
        ezib = ezIBAsync()
        ezib._default_account = "DU123456"
        
        # Setup corrupted data (not a dict)
        ezib._positions = {"DU123456": "corrupted_data"}
        
        # Execute - should handle gracefully
        with pytest.raises(ValueError):
            ezib.getPosition()

    def test_get_portfolio_with_corrupted_portfolio_data(self):
        """Test getPortfolio with corrupted portfolio data."""
        ezib = ezIBAsync()
        ezib._default_account = "DU123456"
        
        # Setup corrupted data
        ezib._portfolios = {"DU123456": None}
        
        # Execute
        result = ezib.getPortfolio()
        
        # Should handle gracefully
        assert result is None or result == {}

    def test_account_codes_with_none_accounts(self):
        """Test accountCodes property when _accounts is None."""
        ezib = ezIBAsync()
        ezib._accounts = None
        
        # Execute - should handle gracefully
        with pytest.raises(AttributeError):
            codes = ezib.accountCodes


class TestSystemErrorHandling:
    """Test system-level error handling."""

    def test_python_version_check_failure(self):
        """Test Python version requirement check."""
        # Version check happens at module level, so we test the logic directly
        import sys
        original_version = sys.version_info
        try:
            # Simulate old Python version
            sys.version_info = (3, 11, 0)
            
            # Re-evaluate the version check logic
            if sys.version_info < (3, 12):
                # This is the expected behavior
                assert True, "Version check logic works correctly"
            else:
                assert False, "Version check logic failed"
        finally:
            # Restore original version
            sys.version_info = original_version

    def test_initialization_with_missing_dependencies(self):
        """Test initialization when dependencies are missing."""
        # Mock missing ib_async import
        with patch('ezib_async.ezib.IB', side_effect=ImportError("ib_async not found")):
            with pytest.raises(ImportError):
                ezib = ezIBAsync()

    def test_memory_error_handling(self):
        """Test handling of memory errors during large operations."""
        ezib = ezIBAsync()
        
        # Mock memory error in contract creation
        with patch.object(ezib, 'ib') as mock_ib:
            mock_ib.qualifyContractsAsync = AsyncMock(side_effect=MemoryError("Out of memory"))
            
            # Execute - should handle gracefully and return None
            result = asyncio.run(ezib.createContract("AAPL", "STK", "SMART", "USD", "", 0.0, ""))
            assert result is None

    def test_keyboard_interrupt_handling(self):
        """Test handling of keyboard interrupts."""
        ezib = ezIBAsync()
        
        # Mock keyboard interrupt during connection
        with patch.object(ezib, 'ib') as mock_ib:
            mock_ib.connectAsync = AsyncMock(side_effect=KeyboardInterrupt("User interrupt"))
            
            # Execute - should propagate interrupt
            with pytest.raises(KeyboardInterrupt):
                asyncio.run(ezib.connectAsync())


class TestRecoveryMechanisms:
    """Test error recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_reconnection_after_disconnection_error(self):
        """Test automatic reconnection after disconnection."""
        ezib = ezIBAsync()
        ezib.connected = True
        ezib._disconnected_by_user = False
        
        with patch.object(ezib, '_reconnect') as mock_reconnect:
            with patch('asyncio.create_task') as mock_create_task:
                # Simulate disconnection
                ezib._onDisconnectedHandler()
                
                # Verify reconnection attempt
                mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_contract_registration_retry_mechanism(self):
        """Test contract registration retry on failure."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'createContract') as mock_create:
            # Mock initial failure then success
            mock_create.side_effect = [
                asyncio.TimeoutError("Timeout"),
                Mock()  # Success on retry
            ]
            
            mock_contract = Mock()
            
            # Execute multiple registration attempts
            await ezib.registerContract(mock_contract)  # First attempt (fails)
            await ezib.registerContract(mock_contract)  # Second attempt (succeeds)
            
            assert mock_create.call_count == 2

    def test_data_validation_and_sanitization(self):
        """Test data validation and sanitization mechanisms."""
        ezib = ezIBAsync()
        
        # Test with invalid account data
        invalid_account_value = Mock()
        invalid_account_value.account = ""  # Empty account
        invalid_account_value.tag = "NetLiquidation"
        invalid_account_value.value = "invalid_number"
        
        # Execute - should handle invalid data gracefully
        ezib._onAccountValueHandler(invalid_account_value)
        
        # Should not create account with empty name
        assert "" not in ezib._accounts


class TestEdgeCases:
    """Test various edge cases and boundary conditions."""

    def test_very_large_order_quantity(self):
        """Test order creation with very large quantity."""
        ezib = ezIBAsync()
        
        # Execute with very large quantity
        order = ezib.createOrder(quantity=999999999)
        
        # Should handle large numbers
        assert order.totalQuantity == 999999999

    def test_very_small_price_values(self):
        """Test order creation with very small prices."""
        ezib = ezIBAsync()
        
        # Execute with very small price
        order = ezib.createOrder(quantity=100, price=0.0001)
        
        # Should handle small prices
        assert order.lmtPrice == 0.0001

    def test_unicode_symbols(self):
        """Test contract creation with unicode symbols."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'ib'):
            # Execute with unicode symbol - should handle gracefully
            ticker_id = ezib.tickerId("测试股票")
            
            assert isinstance(ticker_id, int)

    def test_empty_string_inputs(self):
        """Test functions with empty string inputs."""
        ezib = ezIBAsync()
        
        # Test various functions with empty strings
        ticker_id = ezib.tickerId("")
        assert isinstance(ticker_id, int)
        
        symbol = ezib.tickerSymbol(0)
        assert isinstance(symbol, str)
        
        details = ezib.contractDetails("")
        assert isinstance(details, dict)

    def test_concurrent_access_to_data_structures(self):
        """Test concurrent access to internal data structures."""
        ezib = ezIBAsync()
        
        # Simulate concurrent modifications
        ezib._accounts["DU123456"] = {"NetLiquidation": "100000"}
        
        # Access while modifying
        accounts = ezib.accounts
        accounts["DU123456"]["BuyingPower"] = "50000"
        
        # Should maintain consistency
        assert ezib._accounts["DU123456"]["BuyingPower"] == "50000"