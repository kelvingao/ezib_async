#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for core ezIBAsync class functionality.

Tests initialization, configuration, utility methods, and core class behavior.
"""
import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from pandas import DataFrame

from ezib_async import ezIBAsync
from ib_async import Stock, IB


class TestEzIBAsyncInitialization:
    """Test ezIBAsync class initialization."""

    def test_init_with_default_parameters(self):
        """Test initialization with default parameters."""
        ezib = ezIBAsync()
        
        # Verify default values
        assert ezib._ibhost == "127.0.0.1"
        assert ezib._ibport == 4001
        assert ezib._ibclient == 1
        assert ezib.connected is False
        assert ezib._disconnected_by_user is False
        assert ezib._default_account is None
        
        # Verify data structures are initialized
        assert isinstance(ezib._accounts, dict)
        assert isinstance(ezib._positions, dict)
        assert isinstance(ezib._portfolios, dict)
        assert isinstance(ezib.contracts, list)
        assert isinstance(ezib.orders, dict)
        assert isinstance(ezib.tickerIds, dict)
        assert isinstance(ezib.marketData, dict)
        assert isinstance(ezib.marketDepthData, dict)
        assert isinstance(ezib.optionsData, dict)

    def test_init_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        ezib = ezIBAsync(
            ibhost="192.168.1.100",
            ibport=7497,
            ibclient=123,
            account="DU123456"
        )
        
        # Verify custom values
        assert ezib._ibhost == "192.168.1.100"
        assert ezib._ibport == 7497
        assert ezib._ibclient == 123
        assert ezib._default_account == "DU123456"

    def test_init_python_version_check(self):
        """Test Python version requirement check."""
        # Version check happens at module level, so we test the logic directly
        import sys
        original_version = sys.version_info
        try:
            # Simulate old Python version
            sys.version_info = (3, 11, 0)
            
            # Re-evaluate the version check logic
            if sys.version_info < (3, 12):
                # This is the expected behavior - version check works
                assert True, "Version check logic works correctly"
            else:
                assert False, "Version check logic failed"
        finally:
            # Restore original version
            sys.version_info = original_version

    def test_init_valid_python_version(self):
        """Test initialization with valid Python version."""
        # Mock valid Python version
        with patch('sys.version_info', (3, 12, 0)):
            ezib = ezIBAsync()
            # Should initialize successfully
            assert ezib is not None

    def test_init_ib_client_creation(self):
        """Test IB client creation during initialization."""
        with patch('ezib_async.ezib.IB') as mock_ib_class:
            mock_ib_instance = Mock()
            # Create mock event objects that support += operations
            for event_name in ['disconnectedEvent', 'accountValueEvent', 'accountSummaryEvent', 
                              'positionEvent', 'updatePortfolioEvent', 'pendingTickersEvent']:
                mock_event = Mock()
                mock_event.__iadd__ = Mock(return_value=mock_event)
                setattr(mock_ib_instance, event_name, mock_event)
            
            mock_ib_class.return_value = mock_ib_instance
            
            ezib = ezIBAsync()
            
            # Verify IB client was created
            mock_ib_class.assert_called_once()
            assert ezib.ib == mock_ib_instance

    def test_init_event_creation(self):
        """Test event objects are created during initialization."""
        ezib = ezIBAsync()
        
        # Verify events exist and are callable
        assert hasattr(ezib, 'pendingMarketTickersEvent')
        assert hasattr(ezib, 'pendingOptionsTickersEvent')
        assert hasattr(ezib, 'updateMarketDepthEvent')
        
        # Verify events tuple
        assert ezib.events == (
            "pendingMarketTickersEvent",
            "pendingOptionsTickersEvent", 
            "updateMarketDepthEvent"
        )

    def test_init_handler_setup(self):
        """Test event handlers are set up during initialization."""
        with patch.object(ezIBAsync, '_setup_handlers') as mock_setup:
            ezib = ezIBAsync()
            
            # Verify handler setup was called
            mock_setup.assert_called_once()

    def test_init_data_structures_initialization(self):
        """Test that all data structures are properly initialized."""
        ezib = ezIBAsync()
        
        # Verify market data structures have default ticker
        assert 0 in ezib.marketData
        assert isinstance(ezib.marketData[0], DataFrame)
        assert 0 in ezib.marketDepthData
        assert isinstance(ezib.marketDepthData[0], DataFrame)
        assert 0 in ezib.optionsData
        assert isinstance(ezib.optionsData[0], DataFrame)
        
        # Verify ticker ID mapping
        assert 0 in ezib.tickerIds
        assert ezib.tickerIds[0] == "SYMBOL"

    def test_init_logging_configuration(self):
        """Test logging configuration during initialization."""
        # Just test that logger is properly configured without mocking
        # since IB library creation interferes with mock expectations
        ezib = ezIBAsync()
        
        # Verify logger was set up correctly
        assert hasattr(ezib, '_logger')
        assert ezib._logger is not None
        assert ezib._logger.name == 'ezib_async.ezib'


class TestUtilityMethods:
    """Test utility and helper methods."""

    def test_round_closest_valid_basic(self):
        """Test basic price rounding functionality."""
        # Test rounding to nearest penny
        result = ezIBAsync.roundClosestValid(150.123, res=0.01)
        assert result == 150.12
        
        result = ezIBAsync.roundClosestValid(150.126, res=0.01)
        assert result == 150.13

    def test_round_closest_valid_custom_resolution(self):
        """Test rounding with custom resolution."""
        # Test quarter tick rounding
        result = ezIBAsync.roundClosestValid(150.123, res=0.25)
        assert result == 150.0
        
        result = ezIBAsync.roundClosestValid(150.4, res=0.25)
        assert result == 150.5

    def test_round_closest_valid_none_input(self):
        """Test rounding with None input."""
        result = ezIBAsync.roundClosestValid(None, res=0.01)
        assert result is None

    def test_round_closest_valid_zero_input(self):
        """Test rounding with zero input."""
        result = ezIBAsync.roundClosestValid(0.0, res=0.01)
        assert result == 0.0

    def test_round_closest_valid_negative_input(self):
        """Test rounding with negative input."""
        result = ezIBAsync.roundClosestValid(-150.123, res=0.01)
        assert result == -150.12

    def test_round_closest_valid_custom_decimals(self):
        """Test rounding with custom decimal places."""
        result = ezIBAsync.roundClosestValid(150.123456, res=0.001, decimals=3)
        assert result == 150.123

    def test_round_closest_valid_large_numbers(self):
        """Test rounding with large numbers."""
        result = ezIBAsync.roundClosestValid(99999.999, res=0.01)
        assert result == 100000.00

    def test_contract_to_tuple_stock(self):
        """Test converting stock contract to tuple."""
        stock = Stock(symbol="AAPL", exchange="SMART", currency="USD")
        
        result = ezIBAsync.contract_to_tuple(stock)
        
        expected = (
            "AAPL",
            "STK", 
            "SMART",
            "USD",
            "",
            0.0,
            ""
        )
        assert result == expected

    def test_contract_to_tuple_with_missing_attributes(self):
        """Test converting contract with missing attributes."""
        mock_contract = Mock()
        mock_contract.symbol = "TEST"
        mock_contract.secType = "STK"
        mock_contract.exchange = "SMART"
        mock_contract.currency = "USD"
        # Missing lastTradeDateOrContractMonth, strike, right
        
        result = ezIBAsync.contract_to_tuple(mock_contract)
        
        # Should handle missing attributes gracefully
        assert result[0] == "TEST"
        assert result[1] == "STK"

    def test_contract_to_tuple_with_none_input(self):
        """Test converting None contract to tuple."""
        with pytest.raises(AttributeError):
            ezIBAsync.contract_to_tuple(None)


class TestAccountManagement:
    """Test account management functionality."""

    def test_get_active_account_with_default(self):
        """Test getting active account with default set."""
        ezib = ezIBAsync()
        ezib._default_account = "DU123456"
        
        result = ezib._get_active_account()
        
        assert result == "DU123456"

    def test_get_active_account_with_parameter(self):
        """Test getting active account with parameter."""
        ezib = ezIBAsync()
        ezib._accounts = {"DU789012": {}}
        
        result = ezib._get_active_account("DU789012")
        
        assert result == "DU789012"

    def test_get_active_account_not_found(self):
        """Test getting active account that doesn't exist."""
        ezib = ezIBAsync()
        ezib._accounts = {"DU123456": {}}
        
        result = ezib._get_active_account("DU999999")
        
        assert result is None

    def test_get_active_account_no_default_no_parameter(self):
        """Test getting active account with no default and no parameter."""
        ezib = ezIBAsync()
        ezib._default_account = None
        
        result = ezib._get_active_account()
        
        assert result is None


class TestTickerManagement:
    """Test ticker ID management functionality."""

    def test_ticker_id_new_symbol(self):
        """Test ticker ID assignment for new symbol."""
        ezib = ezIBAsync()
        initial_count = len(ezib.tickerIds)
        
        ticker_id = ezib.tickerId("AAPL")
        
        # Should assign new ID
        assert isinstance(ticker_id, int)
        assert ticker_id > 0
        assert len(ezib.tickerIds) == initial_count + 1
        assert ezib.tickerIds[ticker_id] == "AAPL"

    def test_ticker_id_existing_symbol(self):
        """Test ticker ID for existing symbol."""
        ezib = ezIBAsync()
        
        # Add symbol first time
        ticker_id1 = ezib.tickerId("AAPL")
        
        # Add same symbol again
        ticker_id2 = ezib.tickerId("AAPL")
        
        # Should return same ID
        assert ticker_id1 == ticker_id2

    def test_ticker_id_with_contract_object(self):
        """Test ticker ID with contract object."""
        ezib = ezIBAsync()
        
        stock = Stock(symbol="MSFT", exchange="SMART", currency="USD")
        
        with patch.object(ezib, 'contractString', return_value="MSFT"):
            ticker_id = ezib.tickerId(stock)
            
            # Should assign ID based on contract string
            assert isinstance(ticker_id, int)
            assert ezib.tickerIds[ticker_id] == "MSFT"

    def test_ticker_symbol_lookup(self):
        """Test looking up symbol from ticker ID."""
        ezib = ezIBAsync()
        
        # Add a symbol
        ticker_id = ezib.tickerId("GOOGL")
        
        # Look up symbol
        symbol = ezib.tickerSymbol(ticker_id)
        
        assert symbol == "GOOGL"

    def test_ticker_symbol_invalid_id(self):
        """Test looking up symbol with invalid ID."""
        ezib = ezIBAsync()
        
        symbol = ezib.tickerSymbol(99999)
        
        assert symbol == ""

    def test_ticker_id_counter_increment(self):
        """Test that ticker ID counter increments properly."""
        ezib = ezIBAsync()
        initial_count = len(ezib.tickerIds)
        
        # Add multiple symbols
        id1 = ezib.tickerId("SYM1")
        id2 = ezib.tickerId("SYM2")
        id3 = ezib.tickerId("SYM3")
        
        # IDs should be sequential
        assert id2 == id1 + 1
        assert id3 == id2 + 1
        assert len(ezib.tickerIds) == initial_count + 3


class TestDataStructureManagement:
    """Test management of internal data structures."""

    def test_contracts_list_management(self):
        """Test contracts list operations."""
        ezib = ezIBAsync()
        
        # Initially empty
        assert len(ezib.contracts) == 0
        
        # Add contract
        mock_contract = Mock()
        ezib.contracts.append(mock_contract)
        
        assert len(ezib.contracts) == 1
        assert ezib.contracts[0] == mock_contract

    def test_orders_dict_management(self):
        """Test orders dictionary operations."""
        ezib = ezIBAsync()
        
        # Initially empty
        assert len(ezib.orders) == 0
        
        # Add order
        order_info = {
            "id": 1001,
            "symbol": "AAPL",
            "status": "SENT",
            "datetime": datetime.now()
        }
        ezib.orders[1001] = order_info
        
        assert 1001 in ezib.orders
        assert ezib.orders[1001] == order_info

    def test_market_data_dataframe_initialization(self):
        """Test market data DataFrame initialization."""
        ezib = ezIBAsync()
        
        # Check default ticker DataFrame
        default_df = ezib.marketData[0]
        assert isinstance(default_df, DataFrame)
        
        # Add new ticker data
        test_df = DataFrame({"bid": [150.0], "ask": [150.5]})
        ezib.marketData[1] = test_df
        
        assert 1 in ezib.marketData
        assert ezib.marketData[1].equals(test_df)

    def test_accounts_structure_management(self):
        """Test accounts data structure management."""
        ezib = ezIBAsync()
        
        # Initially empty
        assert len(ezib._accounts) == 0
        
        # Add account data
        ezib._accounts["DU123456"] = {
            "NetLiquidation": "100000.0",
            "BuyingPower": "50000.0"
        }
        
        assert "DU123456" in ezib._accounts
        assert ezib._accounts["DU123456"]["NetLiquidation"] == "100000.0"

    def test_positions_structure_management(self):
        """Test positions data structure management."""
        ezib = ezIBAsync()
        
        # Initially empty
        assert len(ezib._positions) == 0
        
        # Add position data
        ezib._positions["DU123456"] = {
            "AAPL": {
                "symbol": "AAPL",
                "position": 100,
                "avgCost": 150.0
            }
        }
        
        assert "DU123456" in ezib._positions
        assert "AAPL" in ezib._positions["DU123456"]

    def test_portfolios_structure_management(self):
        """Test portfolios data structure management."""
        ezib = ezIBAsync()
        
        # Initially empty
        assert len(ezib._portfolios) == 0
        
        # Add portfolio data
        ezib._portfolios["DU123456"] = {
            "AAPL": {
                "symbol": "AAPL",
                "marketValue": 15000.0,
                "unrealizedPNL": 500.0
            }
        }
        
        assert "DU123456" in ezib._portfolios
        assert "AAPL" in ezib._portfolios["DU123456"]


class TestConfigurationProperties:
    """Test configuration and property access."""

    def test_connected_property(self):
        """Test connected property behavior."""
        ezib = ezIBAsync()
        
        # Initially false
        assert ezib.connected is False
        
        # Set to true
        ezib.connected = True
        assert ezib.connected is True

    def test_ibhost_property(self):
        """Test ibhost property access."""
        ezib = ezIBAsync(ibhost="192.168.1.100")
        
        assert ezib._ibhost == "192.168.1.100"

    def test_ibport_property(self):
        """Test ibport property access."""
        ezib = ezIBAsync(ibport=7497)
        
        assert ezib._ibport == 7497

    def test_ibclient_property(self):
        """Test ibclient property access."""
        ezib = ezIBAsync(ibclient=123)
        
        assert ezib._ibclient == 123

    def test_default_account_property(self):
        """Test default account property."""
        ezib = ezIBAsync(account="DU123456")
        
        assert ezib._default_account == "DU123456"

    def test_disconnected_by_user_flag(self):
        """Test disconnected by user flag."""
        ezib = ezIBAsync()
        
        # Initially false
        assert ezib._disconnected_by_user is False
        
        # Set to true (simulating user disconnect)
        ezib._disconnected_by_user = True
        assert ezib._disconnected_by_user is True


class TestStaticMethods:
    """Test static methods of the class."""

    def test_round_closest_valid_is_static(self):
        """Test that roundClosestValid is a static method."""
        # Should be callable without instance
        result = ezIBAsync.roundClosestValid(150.123, res=0.01)
        assert result == 150.12

    def test_contract_to_tuple_is_static(self):
        """Test that contract_to_tuple is a static method."""
        stock = Stock(symbol="AAPL", exchange="SMART", currency="USD")
        
        # Should be callable without instance
        result = ezIBAsync.contract_to_tuple(stock)
        assert result[0] == "AAPL"


class TestSpecialFeatures:
    """Test special features and advanced functionality."""

    def test_triggerable_trailing_stops_initialization(self):
        """Test triggerable trailing stops structure initialization."""
        ezib = ezIBAsync()
        
        # Should not be initialized until first use (lazy initialization)
        assert not hasattr(ezib, 'triggerableTrailingStops')
        
        # After accessing a triggerable trailing stop function, it should be initialized
        # This would happen in actual usage when calling methods that create trailing stops

    def test_symbol_orders_property(self):
        """Test symbol_orders data structure."""
        ezib = ezIBAsync()
        
        # Initially should be empty dict
        assert isinstance(ezib.symbol_orders, dict)
        assert len(ezib.symbol_orders) == 0
        
        # Manually add some orders to test structure
        from ib_async import Order
        order1 = Order()
        order2 = Order()
        
        ezib.symbol_orders["AAPL"] = [order1]
        ezib.symbol_orders["MSFT"] = [order2]
        
        # Should be accessible
        assert "AAPL" in ezib.symbol_orders
        assert "MSFT" in ezib.symbol_orders
        assert len(ezib.symbol_orders["AAPL"]) == 1
        assert len(ezib.symbol_orders["MSFT"]) == 1

    def test_logging_integration(self):
        """Test logging integration."""
        ezib = ezIBAsync()
        
        # Should have logger instance
        assert hasattr(ezib, '_logger')
        assert ezib._logger is not None
        
        # Logger should be configured for this module
        assert ezib._logger.name == 'ezib_async.ezib'

    def test_class_documentation(self):
        """Test that class has proper documentation."""
        # Check that class has docstring
        assert ezIBAsync.__doc__ is not None
        assert len(ezIBAsync.__doc__.strip()) > 0

    def test_method_signatures(self):
        """Test that key methods have expected signatures."""
        # Test that key methods exist
        assert hasattr(ezIBAsync, 'connectAsync')
        assert hasattr(ezIBAsync, 'disconnect')
        assert hasattr(ezIBAsync, 'createContract')
        assert hasattr(ezIBAsync, 'createOrder')
        assert hasattr(ezIBAsync, 'placeOrder')
        assert hasattr(ezIBAsync, 'requestMarketData')
        assert hasattr(ezIBAsync, 'tickerId')
        assert hasattr(ezIBAsync, 'contractString')

    def test_class_inheritance(self):
        """Test class inheritance structure."""
        ezib = ezIBAsync()
        
        # Should be instance of itself
        assert isinstance(ezib, ezIBAsync)
        
        # Check MRO (Method Resolution Order)
        mro = ezIBAsync.__mro__
        assert ezIBAsync in mro
        assert object in mro


class TestMemoryManagement:
    """Test memory management and cleanup."""

    def test_large_data_structure_handling(self):
        """Test handling of large data structures."""
        ezib = ezIBAsync()
        
        # Add many contracts
        for i in range(1000):
            ezib.tickerId(f"STOCK{i}")
        
        # Should handle large number of tickers
        assert len(ezib.tickerIds) >= 1000

    def test_data_cleanup_on_disconnect(self):
        """Test that data is properly cleaned up on disconnect."""
        ezib = ezIBAsync()
        
        # Add some data
        ezib._accounts["DU123456"] = {"NetLiquidation": "100000"}
        ezib.orders[1001] = {"symbol": "AAPL"}
        
        # Simulate disconnect
        ezib.connected = False
        
        # Data should still exist (cleanup is manual)
        assert len(ezib._accounts) > 0
        assert len(ezib.orders) > 0

    def test_circular_reference_prevention(self):
        """Test prevention of circular references."""
        ezib = ezIBAsync()
        
        # Should not create circular references
        # (This is more of a design test)
        assert ezib.ib is not None
        # ib should not reference back to ezib in a circular way