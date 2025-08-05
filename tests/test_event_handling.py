#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for event handling functionality in ezIBAsync.

Tests eventkit event system, event handlers, and callback mechanisms.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from ezib_async import ezIBAsync
# Import helper functions from conftest directly
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from conftest import create_mock_account_value, create_mock_position, create_mock_portfolio_item
from ib_async import AccountValue, Position, PortfolioItem


class TestEventCreation:
    """Test event creation and initialization."""

    def test_create_events(self):
        """Test event objects are created during initialization."""
        # Create real instance
        ezib = ezIBAsync()
        
        # Verify events exist
        assert hasattr(ezib, 'pendingMarketTickersEvent')
        assert hasattr(ezib, 'pendingOptionsTickersEvent') 
        assert hasattr(ezib, 'updateMarketDepthEvent')
        
        # Verify events are in the events tuple
        expected_events = (
            "pendingMarketTickersEvent",
            "pendingOptionsTickersEvent", 
            "updateMarketDepthEvent"
        )
        assert ezib.events == expected_events

    def test_events_are_callable(self):
        """Test that events can be called/emitted."""
        ezib = ezIBAsync()
        
        # Test events can be emitted (should not raise exception)
        ezib.pendingMarketTickersEvent.emit([])
        ezib.pendingOptionsTickersEvent.emit([])
        ezib.updateMarketDepthEvent.emit([])


class TestEventHandlerSetup:
    """Test event handler registration."""

    def test_setup_handlers_called_during_init(self):
        """Test that _setup_handlers is called during initialization."""
        with patch.object(ezIBAsync, '_setup_handlers') as mock_setup:
            # Create instance
            ezib = ezIBAsync()
            
            # Verify setup was called
            mock_setup.assert_called_once()

    def test_setup_handlers_registers_ib_events(self):
        """Test that _setup_handlers registers IB event handlers."""
        ezib = ezIBAsync()
        
        # Mock IB client
        with patch.object(ezib, 'ib') as mock_ib:
            # Setup event objects on mock that support += operator
            for event_name in ['disconnectedEvent', 'accountValueEvent', 'accountSummaryEvent', 
                              'positionEvent', 'updatePortfolioEvent', 'pendingTickersEvent']:
                mock_event = Mock()
                mock_event.__iadd__ = Mock(return_value=mock_event)
                setattr(mock_ib, event_name, mock_event)
            
            # Call setup handlers
            ezib._setup_handlers()
            
            # Verify handlers were registered (events support += operator)
            mock_ib.disconnectedEvent.__iadd__.assert_called_once()
            mock_ib.accountValueEvent.__iadd__.assert_called_once()
            mock_ib.accountSummaryEvent.__iadd__.assert_called_once()
            mock_ib.positionEvent.__iadd__.assert_called_once()
            mock_ib.updatePortfolioEvent.__iadd__.assert_called_once()
            mock_ib.pendingTickersEvent.__iadd__.assert_called_once()

    def test_setup_handlers_with_none_ib(self):
        """Test _setup_handlers when ib client is None."""
        ezib = ezIBAsync()
        ezib.ib = None
        
        # Should not raise exception
        ezib._setup_handlers()


class TestAccountValueEventHandling:
    """Test account value event handling."""

    def test_on_account_value_handler_new_account(self):
        """Test handling account value for new account."""
        ezib = ezIBAsync()
        
        # Create mock account value
        account_value = create_mock_account_value(
            tag="NetLiquidation", 
            value="100000.0", 
            account="DU123456"
        )
        
        # Execute
        ezib._onAccountValueHandler(account_value)
        
        # Verify account was created and value set
        assert "DU123456" in ezib._accounts
        assert ezib._accounts["DU123456"]["NetLiquidation"] == "100000.0"

    def test_on_account_value_handler_existing_account(self):
        """Test handling account value for existing account."""
        ezib = ezIBAsync()
        
        # Setup existing account
        ezib._accounts["DU123456"] = {"ExistingTag": "1000.0"}
        
        # Create mock account value
        account_value = create_mock_account_value(
            tag="NewTag", 
            value="2000.0", 
            account="DU123456"
        )
        
        # Execute
        ezib._onAccountValueHandler(account_value)
        
        # Verify both values exist
        assert ezib._accounts["DU123456"]["ExistingTag"] == "1000.0"
        assert ezib._accounts["DU123456"]["NewTag"] == "2000.0"

    def test_on_account_value_handler_error_handling(self):
        """Test account value handler error handling."""
        ezib = ezIBAsync()
        
        # Create invalid account value that will cause error
        invalid_value = Mock()
        invalid_value.account = None  # This will cause KeyError
        
        # Should not raise exception
        ezib._onAccountValueHandler(invalid_value)
        
        # Verify no accounts were created
        assert len(ezib._accounts) == 0


class TestAccountSummaryEventHandling:
    """Test account summary event handling."""

    def test_on_account_summary_handler(self):
        """Test handling account summary updates."""
        ezib = ezIBAsync()
        ezib._accounts_summary = {}
        
        # Create mock account summary
        mock_summary = Mock()
        mock_summary.account = "DU123456"
        mock_summary.tag = "NetLiquidation" 
        mock_summary.value = "100000.0"
        
        # Execute
        ezib._onAccountSummaryHandler(mock_summary)
        
        # Verify summary was stored
        assert "DU123456" in ezib._accounts_summary
        assert mock_summary in ezib._accounts_summary["DU123456"]

    def test_on_account_summary_handler_error(self):
        """Test account summary handler error handling."""
        ezib = ezIBAsync()
        ezib._accounts_summary = {}
        
        # Create invalid summary
        invalid_summary = Mock()
        invalid_summary.account = None
        
        # Should not raise exception  
        ezib._onAccountSummaryHandler(invalid_summary)


class TestPositionEventHandling:
    """Test position event handling."""

    def test_on_position_update_handler_new_position(self):
        """Test handling new position update."""
        ezib = ezIBAsync()
        
        # Create mock position
        position = create_mock_position(
            symbol="AAPL", 
            position=100, 
            avg_cost=150.0, 
            account="DU123456"
        )
        
        with patch.object(ezib, 'registerContract') as mock_register:
            with patch.object(ezib, 'contractString', return_value="AAPL"):
                # Execute
                ezib._onPositionUpdateHandler(position)
                
                # Verify position was stored
                assert "DU123456" in ezib._positions
                assert "AAPL" in ezib._positions["DU123456"]
                
                position_data = ezib._positions["DU123456"]["AAPL"]
                assert position_data["symbol"] == "AAPL"
                assert position_data["position"] == 100
                assert position_data["avgCost"] == 150.0
                assert position_data["account"] == "DU123456"
                
                # Verify contract registration was attempted
                mock_register.assert_called_once()

    def test_on_position_update_handler_existing_position(self):
        """Test updating existing position."""
        ezib = ezIBAsync()
        
        # Setup existing position
        ezib._positions["DU123456"] = {
            "AAPL": {
                "symbol": "AAPL",
                "position": 50,
                "avgCost": 140.0,
                "account": "DU123456"
            }
        }
        
        # Create updated position
        position = create_mock_position(
            symbol="AAPL", 
            position=150, 
            avg_cost=155.0, 
            account="DU123456"
        )
        
        with patch.object(ezib, 'registerContract'):
            with patch.object(ezib, 'contractString', return_value="AAPL"):
                # Execute
                ezib._onPositionUpdateHandler(position)
                
                # Verify position was updated
                position_data = ezib._positions["DU123456"]["AAPL"]
                assert position_data["position"] == 150
                assert position_data["avgCost"] == 155.0

    def test_on_position_update_handler_error(self):
        """Test position update handler error handling."""
        ezib = ezIBAsync()
        
        # Create invalid position
        invalid_position = Mock()
        invalid_position.contract = None  # Will cause error
        
        # Should not raise exception
        ezib._onPositionUpdateHandler(invalid_position)


class TestPortfolioEventHandling: 
    """Test portfolio event handling."""

    def test_on_portfolio_update_handler_new_item(self):
        """Test handling new portfolio item."""
        ezib = ezIBAsync()
        
        # Create mock portfolio item
        portfolio_item = create_mock_portfolio_item(
            symbol="AAPL",
            position=100,
            market_price=150.0,
            market_value=15000.0,
            avg_cost=145.0,
            unrealized_pnl=500.0,
            realized_pnl=0.0,
            account="DU123456"
        )
        
        with patch.object(ezib, 'contractString', return_value="AAPL"):
            # Execute
            ezib._onPortfolioUpdateHandler(portfolio_item)
            
            # Verify portfolio item was stored
            assert "DU123456" in ezib._portfolios
            assert "AAPL" in ezib._portfolios["DU123456"]
            
            portfolio_data = ezib._portfolios["DU123456"]["AAPL"]
            assert portfolio_data["symbol"] == "AAPL"
            assert portfolio_data["position"] == 100
            assert portfolio_data["marketPrice"] == 150.0
            assert portfolio_data["marketValue"] == 15000.0
            assert portfolio_data["averageCost"] == 145.0
            assert portfolio_data["unrealizedPNL"] == 500.0
            assert portfolio_data["realizedPNL"] == 0.0
            assert portfolio_data["totalPNL"] == 500.0  # unrealized + realized
            assert portfolio_data["account"] == "DU123456"

    def test_on_portfolio_update_handler_total_pnl_calculation(self):
        """Test total P&L calculation in portfolio update."""
        ezib = ezIBAsync()
        
        # Create portfolio item with both realized and unrealized P&L
        portfolio_item = create_mock_portfolio_item(
            symbol="MSFT",
            unrealized_pnl=300.0,
            realized_pnl=150.0,
            account="DU123456"
        )
        
        with patch.object(ezib, 'contractString', return_value="MSFT"):
            # Execute
            ezib._onPortfolioUpdateHandler(portfolio_item)
            
            # Verify total P&L calculation
            portfolio_data = ezib._portfolios["DU123456"]["MSFT"]
            assert portfolio_data["totalPNL"] == 450.0  # 300 + 150

    def test_on_portfolio_update_handler_error(self):
        """Test portfolio update handler error handling."""
        ezib = ezIBAsync()
        
        # Create invalid portfolio item
        invalid_item = Mock()
        invalid_item.contract = None  # Will cause error
        
        # Should not raise exception
        ezib._onPortfolioUpdateHandler(invalid_item)


class TestDisconnectedEventHandling:
    """Test disconnection event handling."""

    def test_on_disconnected_handler_sets_connected_false(self):
        """Test disconnection handler sets connected to False."""
        ezib = ezIBAsync()
        ezib.connected = True
        ezib._disconnected_by_user = False
        
        with patch('asyncio.create_task') as mock_create_task:
            # Execute
            ezib._onDisconnectedHandler()
            
            # Verify connection state
            assert ezib.connected is False
            
            # Verify reconnection task was created
            mock_create_task.assert_called_once()

    def test_on_disconnected_handler_user_disconnected(self):
        """Test disconnection handler when user initiated disconnect."""
        ezib = ezIBAsync()
        ezib.connected = True
        ezib._disconnected_by_user = True  # User initiated
        
        with patch('asyncio.create_task') as mock_create_task:
            # Execute  
            ezib._onDisconnectedHandler()
            
            # Verify connection state
            assert ezib.connected is False
            
            # Verify no reconnection task was created
            mock_create_task.assert_not_called()


class TestEventSubscriptionAndEmission:
    """Test event subscription and emission functionality."""

    def test_subscribe_to_market_data_event(self):
        """Test subscribing to market data events."""
        ezib = ezIBAsync()
        
        # Create event handler
        received_data = []
        def handler(tickers):
            received_data.extend(tickers)
        
        # Subscribe to event
        ezib.pendingMarketTickersEvent += handler
        
        # Emit event
        test_tickers = [Mock(), Mock()]
        ezib.pendingMarketTickersEvent.emit(test_tickers)
        
        # Verify handler was called
        assert len(received_data) == 2
        assert received_data == test_tickers

    def test_subscribe_to_options_data_event(self):
        """Test subscribing to options data events."""
        ezib = ezIBAsync()
        
        # Create event handler
        received_data = []
        def handler(tickers):
            received_data.extend(tickers)
        
        # Subscribe to event
        ezib.pendingOptionsTickersEvent += handler
        
        # Emit event
        test_tickers = [Mock()]
        ezib.pendingOptionsTickersEvent.emit(test_tickers)
        
        # Verify handler was called
        assert len(received_data) == 1

    def test_subscribe_to_market_depth_event(self):
        """Test subscribing to market depth events."""
        ezib = ezIBAsync()
        
        # Create event handler
        received_data = []
        def handler(tickers):
            if isinstance(tickers, list):
                received_data.extend(tickers)
            else:
                received_data.append(tickers)
        
        # Subscribe to event
        ezib.updateMarketDepthEvent += handler
        
        # Emit event
        test_ticker = Mock()
        ezib.updateMarketDepthEvent.emit(test_ticker)
        
        # Verify handler was called
        assert len(received_data) == 1
        assert received_data[0] == test_ticker

    def test_unsubscribe_from_event(self):
        """Test unsubscribing from events."""
        ezib = ezIBAsync()
        
        # Create event handler
        call_count = 0
        def handler(data):
            nonlocal call_count
            call_count += 1
        
        # Subscribe to event
        ezib.pendingMarketTickersEvent += handler
        
        # Emit event
        ezib.pendingMarketTickersEvent.emit([])
        assert call_count == 1
        
        # Unsubscribe from event
        ezib.pendingMarketTickersEvent -= handler
        
        # Emit event again
        ezib.pendingMarketTickersEvent.emit([])
        
        # Verify handler was not called again
        assert call_count == 1

    def test_multiple_event_handlers(self):
        """Test multiple handlers for same event."""
        ezib = ezIBAsync()
        
        # Create multiple handlers
        handler1_calls = []
        handler2_calls = []
        
        def handler1(data):
            handler1_calls.append(data)
            
        def handler2(data):
            handler2_calls.append(data)
        
        # Subscribe both handlers
        ezib.pendingMarketTickersEvent += handler1
        ezib.pendingMarketTickersEvent += handler2
        
        # Emit event
        test_data = [Mock()]
        ezib.pendingMarketTickersEvent.emit(test_data)
        
        # Verify both handlers were called
        assert len(handler1_calls) == 1
        assert len(handler2_calls) == 1
        assert handler1_calls[0] == test_data
        assert handler2_calls[0] == test_data


class TestEventErrorHandling:
    """Test error handling in event processing."""

    def test_event_handler_exception_handling(self):
        """Test that exceptions in event handlers don't crash the system."""
        ezib = ezIBAsync()
        
        # Create handler that raises exception
        def failing_handler(data):
            raise Exception("Handler error")
        
        # Create normal handler
        normal_calls = []
        def normal_handler(data):
            normal_calls.append(data)
        
        # Subscribe both handlers
        ezib.pendingMarketTickersEvent += failing_handler
        ezib.pendingMarketTickersEvent += normal_handler
        
        # Emit event - should not raise exception
        test_data = [Mock()]
        try:
            ezib.pendingMarketTickersEvent.emit(test_data)
        except Exception as e:
            # If eventkit doesn't handle exceptions, we should at least document it
            pytest.fail(f"Event emission should not raise exceptions: {e}")
        
        # Normal handler should still be called
        assert len(normal_calls) == 1

    def test_account_value_handler_with_invalid_data(self):
        """Test account value handler with completely invalid data."""
        ezib = ezIBAsync()
        
        # Call handler with None
        ezib._onAccountValueHandler(None)
        
        # Call handler with object missing required attributes
        invalid_obj = Mock()
        del invalid_obj.account  # Remove required attribute
        
        # Should not crash
        ezib._onAccountValueHandler(invalid_obj)

    def test_position_handler_with_invalid_data(self):
        """Test position handler with invalid data."""
        ezib = ezIBAsync()
        
        # Call handler with None
        ezib._onPositionUpdateHandler(None)
        
        # Should not crash the system
        assert len(ezib._positions) == 0

    def test_portfolio_handler_with_invalid_data(self):
        """Test portfolio handler with invalid data."""
        ezib = ezIBAsync()
        
        # Call handler with None
        ezib._onPortfolioUpdateHandler(None)
        
        # Should not crash the system
        assert len(ezib._portfolios) == 0


class TestEventIntegration:
    """Integration tests for event handling."""

    def test_complete_event_flow_simulation(self):
        """Test complete event flow from IB to user handlers."""
        ezib = ezIBAsync()
        
        # Setup user event handlers
        market_data_received = []
        account_updates_received = []
        position_updates_received = []
        
        def market_handler(tickers):
            market_data_received.extend(tickers)
            
        def account_handler():
            account_updates_received.append(datetime.now())
            
        def position_handler():
            position_updates_received.append(datetime.now())
        
        # Subscribe to events
        ezib.pendingMarketTickersEvent += market_handler
        
        # Simulate IB events
        
        # 1. Account value update
        account_value = create_mock_account_value()
        ezib._onAccountValueHandler(account_value)
        
        # 2. Position update
        position = create_mock_position()
        with patch.object(ezib, 'contractString', return_value="AAPL"):
            with patch.object(ezib, 'registerContract'):
                ezib._onPositionUpdateHandler(position)
        
        # 3. Market data update
        mock_tickers = [Mock(), Mock()]
        ezib.pendingMarketTickersEvent.emit(mock_tickers)
        
        # Verify all updates were processed
        assert "DU123456" in ezib._accounts
        assert "DU123456" in ezib._positions
        assert len(market_data_received) == 2
        
        # Cleanup
        ezib.pendingMarketTickersEvent -= market_handler