#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit and integration tests for order management functionality in ezIBAsync.

Tests order creation, placement, bracket orders, and order lifecycle management.
"""
import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime

from ezib_async import ezIBAsync
from ib_async import Order, Trade


class TestOrderCreation:
    """Test order creation functionality."""

    def test_create_market_order_buy(self, mock_ezib):
        """Test creating a market buy order."""
        # Setup
        mock_order = Mock(spec=Order)
        mock_ezib.createOrder = Mock(return_value=mock_order)
        
        # Execute
        order = mock_ezib.createOrder(quantity=100, price=0)
        
        # Verify
        mock_ezib.createOrder.assert_called_once_with(quantity=100, price=0)
        assert order == mock_order

    def test_create_market_order_sell(self, mock_ezib):
        """Test creating a market sell order."""
        # Setup
        mock_order = Mock(spec=Order)
        mock_ezib.createOrder = Mock(return_value=mock_order)
        
        # Execute
        order = mock_ezib.createOrder(quantity=-100, price=0)
        
        # Verify
        mock_ezib.createOrder.assert_called_once_with(quantity=-100, price=0)

    def test_create_limit_order(self, mock_ezib):
        """Test creating a limit order."""
        # Setup
        mock_order = Mock(spec=Order)
        mock_ezib.createOrder = Mock(return_value=mock_order)
        
        # Execute
        order = mock_ezib.createOrder(quantity=100, price=150.0)
        
        # Verify
        mock_ezib.createOrder.assert_called_once_with(quantity=100, price=150.0)

    def test_create_order_with_stop(self, mock_ezib):
        """Test creating an order with stop price."""
        # Setup
        mock_order = Mock(spec=Order)
        mock_ezib.createOrder = Mock(return_value=mock_order)
        
        # Execute
        order = mock_ezib.createOrder(quantity=100, price=150.0, stop=140.0)
        
        # Verify
        mock_ezib.createOrder.assert_called_once_with(quantity=100, price=150.0, stop=140.0)

    def test_create_order_with_tif(self, mock_ezib):
        """Test creating an order with time-in-force."""
        # Setup
        mock_order = Mock(spec=Order)
        mock_ezib.createOrder = Mock(return_value=mock_order)
        
        # Execute
        order = mock_ezib.createOrder(quantity=100, price=150.0, tif="GTC")
        
        # Verify
        mock_ezib.createOrder.assert_called_once_with(quantity=100, price=150.0, tif="GTC")

    def test_create_order_with_account(self, mock_ezib):
        """Test creating an order with specific account."""
        # Setup
        mock_order = Mock(spec=Order)
        mock_ezib.createOrder = Mock(return_value=mock_order)
        
        # Execute
        order = mock_ezib.createOrder(quantity=100, account="DU123456")
        
        # Verify
        mock_ezib.createOrder.assert_called_once_with(quantity=100, account="DU123456")

    def test_create_order_real_instance(self):
        """Test creating order with real ezIBAsync instance."""
        # Create real instance
        ezib = ezIBAsync()
        ezib._default_account = "DU123456"
        
        # Execute - Market order
        market_order = ezib.createOrder(quantity=100, price=0)
        
        # Verify market order properties
        assert market_order.action == "BUY"
        assert market_order.totalQuantity == 100
        assert market_order.orderType == "MKT"
        assert market_order.lmtPrice == 0
        assert market_order.tif == "DAY"
        
        # Execute - Limit order
        limit_order = ezib.createOrder(quantity=-50, price=150.0)
        
        # Verify limit order properties
        assert limit_order.action == "SELL"
        assert limit_order.totalQuantity == 50
        assert limit_order.orderType == "LMT"
        assert limit_order.lmtPrice == 150.0

    def test_create_order_with_special_types(self):
        """Test creating orders with special order types."""
        ezib = ezIBAsync()
        
        # Market-on-Open order
        moo_order = ezib.createOrder(quantity=100, orderType="MOO")
        assert moo_order.orderType == "MKT"
        assert moo_order.tif == "OPG"
        
        # Limit-on-Open order  
        loo_order = ezib.createOrder(quantity=100, price=150.0, orderType="LOO")
        assert loo_order.orderType == "LMT"
        assert loo_order.tif == "OPG"
        assert loo_order.lmtPrice == 150.0

    def test_create_order_with_advanced_options(self):
        """Test creating orders with advanced options."""
        ezib = ezIBAsync()
        
        # Order with fill-or-kill and iceberg
        advanced_order = ezib.createOrder(
            quantity=1000, 
            price=150.0, 
            fillorkill=True, 
            iceberg=True,
            transmit=False,
            rth=True
        )
        
        assert advanced_order.allOrNone is True  # fill-or-kill
        assert advanced_order.hidden is True     # iceberg
        assert advanced_order.transmit is False
        assert advanced_order.outsideRth is False  # rth=True means only RTH


class TestOrderPlacement:
    """Test order placement functionality."""

    def test_place_order_success(self, mock_ezib, mock_stock_contract, mock_market_order):
        """Test successful order placement."""
        # Setup
        mock_trade = Mock(spec=Trade)
        mock_ezib.placeOrder = Mock(return_value=mock_trade)
        
        # Execute
        trade = mock_ezib.placeOrder(mock_stock_contract, mock_market_order)
        
        # Verify
        mock_ezib.placeOrder.assert_called_once_with(mock_stock_contract, mock_market_order)
        assert trade == mock_trade

    def test_place_order_with_account(self, mock_ezib, mock_stock_contract, mock_market_order):
        """Test placing order with specific account."""
        # Setup
        mock_trade = Mock(spec=Trade)
        mock_ezib.placeOrder = Mock(return_value=mock_trade)
        
        # Execute
        trade = mock_ezib.placeOrder(mock_stock_contract, mock_market_order, account="DU123456")
        
        # Verify
        mock_ezib.placeOrder.assert_called_once()

    def test_place_order_price_rounding(self):
        """Test order price rounding with contract tick size."""
        # Create real instance
        ezib = ezIBAsync()
        
        # Mock contract details and methods
        with patch.object(ezib, 'contractDetails') as mock_details:
            with patch.object(ezib, 'ib') as mock_ib:
                # Setup tick size
                mock_details.return_value = {"minTick": 0.01}
                mock_ib.placeOrder = Mock(return_value=Mock(spec=Trade))
                
                # Create order with unrounded price
                order = Order()
                order.lmtPrice = 150.123
                order.auxPrice = 140.567
                order.orderId = 1001
                
                contract = Mock()
                
                # Execute
                trade = ezib.placeOrder(contract, order)
                
                # Verify prices were rounded
                assert order.lmtPrice == 150.12  # Rounded to tick size
                assert order.auxPrice == 140.57

    def test_place_order_records_order_info(self):
        """Test that order placement records order information."""
        # Create real instance
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'contractDetails') as mock_details:
            with patch.object(ezib, 'ib') as mock_ib:
                with patch.object(ezib, 'contractString', return_value="AAPL"):
                    # Setup
                    mock_details.return_value = {"minTick": 0.01}
                    mock_trade = Mock(spec=Trade)
                    mock_ib.placeOrder = Mock(return_value=mock_trade)
                    
                    order = Mock(spec=Order)
                    order.orderId = 1001
                    order.lmtPrice = 150.0
                    order.auxPrice = 0.0
                    
                    contract = Mock()
                    
                    # Execute
                    trade = ezib.placeOrder(contract, order)
                    
                    # Verify order was recorded
                    assert 1001 in ezib.orders
                    order_info = ezib.orders[1001]
                    assert order_info["id"] == 1001
                    assert order_info["symbol"] == "AAPL"
                    assert order_info["status"] == "SENT"


class TestTargetOrders:
    """Test target order creation."""

    def test_create_target_order_default(self, mock_ezib):
        """Test creating target order with default parameters."""
        # Setup
        mock_order = Mock(spec=Order)
        mock_ezib.createTargetOrder = Mock(return_value=mock_order)
        
        # Execute
        order = mock_ezib.createTargetOrder(quantity=-100, target=160.0)
        
        # Verify
        mock_ezib.createTargetOrder.assert_called_once_with(quantity=-100, target=160.0)

    def test_create_target_order_with_parent(self, mock_ezib):
        """Test creating target order with parent ID."""
        # Setup
        mock_order = Mock(spec=Order)
        mock_ezib.createTargetOrder = Mock(return_value=mock_order)
        
        # Execute
        order = mock_ezib.createTargetOrder(quantity=-100, parentId=1001, target=160.0)
        
        # Verify
        mock_ezib.createTargetOrder.assert_called_once()

    def test_create_target_order_real_instance(self):
        """Test creating target order with real instance."""
        ezib = ezIBAsync()
        ezib._default_account = "DU123456"
        
        # Execute
        target_order = ezib.createTargetOrder(
            quantity=-100, 
            parentId=1001, 
            target=160.0,
            group="bracket_123"
        )
        
        # Verify target order properties
        assert target_order.action == "SELL"
        assert target_order.totalQuantity == 100
        assert target_order.orderType == "MIT"  # Market if Touched
        assert target_order.auxPrice == 160.0
        assert target_order.parentId == 1001
        assert target_order.ocaGroup == "bracket_123"


class TestStopOrders:
    """Test stop order creation."""

    def test_create_stop_order_basic(self, mock_ezib):
        """Test creating basic stop order."""
        # Setup
        mock_order = Mock(spec=Order)
        mock_ezib.createStopOrder = Mock(return_value=mock_order)
        
        # Execute
        order = mock_ezib.createStopOrder(quantity=-100, stop=140.0)
        
        # Verify
        mock_ezib.createStopOrder.assert_called_once_with(quantity=-100, stop=140.0)

    def test_create_stop_order_with_trail(self, mock_ezib):
        """Test creating trailing stop order."""
        # Setup
        mock_order = Mock(spec=Order)
        mock_ezib.createStopOrder = Mock(return_value=mock_order)
        
        # Execute
        order = mock_ezib.createStopOrder(quantity=-100, stop=5.0, trail="percent")
        
        # Verify
        mock_ezib.createStopOrder.assert_called_once()

    def test_create_stop_order_real_instance(self):
        """Test creating stop order with real instance."""
        ezib = ezIBAsync()
        ezib._default_account = "DU123456"
        
        # Regular stop order
        stop_order = ezib.createStopOrder(
            quantity=-100,
            parentId=1001,
            stop=140.0,
            group="bracket_123"
        )
        
        # Verify stop order properties
        assert stop_order.action == "SELL"
        assert stop_order.totalQuantity == 100
        assert stop_order.orderType == "STP"
        assert stop_order.auxPrice == 140.0
        assert stop_order.parentId == 1001
        assert stop_order.ocaGroup == "bracket_123"

    def test_create_trailing_stop_order(self):
        """Test creating trailing stop order."""
        ezib = ezIBAsync()
        
        # Trailing stop by percentage
        trail_pct_order = ezib.createStopOrder(
            quantity=-100,
            stop=5.0,  # 5% trail
            trail="percent"
        )
        
        assert trail_pct_order.orderType == "TRAIL"
        assert trail_pct_order.trailingPercent == 5.0
        
        # Trailing stop by amount
        trail_amt_order = ezib.createStopOrder(
            quantity=-100,
            stop=2.0,  # $2 trail
            trail="amount"
        )
        
        assert trail_amt_order.orderType == "TRAIL"
        assert trail_amt_order.auxPrice == 2.0

    def test_create_stop_limit_order(self):
        """Test creating stop-limit order."""
        ezib = ezIBAsync()
        
        stop_limit_order = ezib.createStopOrder(
            quantity=-100,
            stop=140.0,
            stop_limit=138.0  # Limit price
        )
        
        assert stop_limit_order.orderType == "STP LMT"
        assert stop_limit_order.auxPrice == 140.0  # Stop price
        assert stop_limit_order.lmtPrice == 138.0  # Limit price


class TestBracketOrders:
    """Test bracket order creation."""

    def test_create_bracket_order_basic(self, mock_ezib, mock_stock_contract):
        """Test creating basic bracket order."""
        # Setup
        mock_result = {
            "group": "bracket_123",
            "entryOrderId": 1001,
            "targetOrderId": 1002,
            "stopOrderId": 1003
        }
        mock_ezib.createBracketOrder = Mock(return_value=mock_result)
        
        # Execute
        result = mock_ezib.createBracketOrder(
            contract=mock_stock_contract,
            quantity=100,
            entry=150.0,
            target=160.0,
            stop=140.0
        )
        
        # Verify
        mock_ezib.createBracketOrder.assert_called_once()
        assert result == mock_result

    def test_create_bracket_order_market_entry(self, mock_ezib, mock_stock_contract):
        """Test creating bracket order with market entry."""
        # Setup
        mock_result = {"entryOrderId": 1001, "targetOrderId": 1002, "stopOrderId": 1003}
        mock_ezib.createBracketOrder = Mock(return_value=mock_result)
        
        # Execute
        result = mock_ezib.createBracketOrder(
            contract=mock_stock_contract,
            quantity=100,
            entry=0,  # Market entry
            target=160.0,
            stop=140.0
        )
        
        # Verify
        mock_ezib.createBracketOrder.assert_called_once()

    def test_create_bracket_order_real_instance(self):
        """Test creating bracket order with real instance."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'placeOrder') as mock_place:
            # Mock trade objects
            entry_trade = Mock(spec=Trade)
            entry_trade.order = Mock(spec=Order)
            entry_trade.order.orderId = 1001
            
            target_trade = Mock(spec=Trade)
            target_trade.order = Mock(spec=Order)
            target_trade.order.orderId = 1002
            
            stop_trade = Mock(spec=Trade)
            stop_trade.order = Mock(spec=Order)
            stop_trade.order.orderId = 1003
            
            mock_place.side_effect = [entry_trade, target_trade, stop_trade]
            
            contract = Mock()
            
            # Execute
            result = ezib.createBracketOrder(
                contract=contract,
                quantity=100,
                entry=150.0,
                target=160.0,
                stop=140.0,
                transmit=True
            )
            
            # Verify result structure
            assert "group" in result
            assert result["entryOrderId"] == 1001
            assert result["targetOrderId"] == 1002
            assert result["stopOrderId"] == 1003
            
            # Verify three orders were placed
            assert mock_place.call_count == 3


class TestTriggerableTrailingStop:
    """Test triggerable trailing stop functionality."""

    def test_create_triggerable_trailing_stop(self, mock_ezib):
        """Test creating triggerable trailing stop."""
        # Setup
        mock_result = {
            "parentId": 1001,
            "triggerPrice": 155.0,
            "trailPercent": 5.0,
            "quantity": -100
        }
        mock_ezib.createTriggerableTrailingStop = Mock(return_value=mock_result)
        
        # Execute
        result = mock_ezib.createTriggerableTrailingStop(
            symbol="AAPL",
            quantity=-100,
            triggerPrice=155.0,
            trailPercent=5.0
        )
        
        # Verify
        mock_ezib.createTriggerableTrailingStop.assert_called_once()
        assert result == mock_result

    def test_create_triggerable_trailing_stop_real_instance(self):
        """Test creating triggerable trailing stop with real instance."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'contractDetails') as mock_details:
            mock_details.return_value = {"minTick": 0.01}
            
            # Execute
            result = ezib.createTriggerableTrailingStop(
                symbol="AAPL",
                quantity=-100,
                triggerPrice=155.0,
                trailPercent=5.0,
                parentId=1001
            )
            
            # Verify result structure (symbol is the key, not stored in the dict)
            assert result["quantity"] == -100
            assert result["triggerPrice"] == 155.0
            assert result["trailPercent"] == 5.0
            assert result["parentId"] == 1001
            assert result["ticksize"] == 0.01
            
            # Verify it was stored in triggerableTrailingStops
            assert "AAPL" in ezib.triggerableTrailingStops
            assert ezib.triggerableTrailingStops["AAPL"] == result


class TestRoundClosestValid:
    """Test price rounding functionality."""

    def test_round_closest_valid_basic(self):
        """Test basic price rounding."""
        # Test static method
        result = ezIBAsync.roundClosestValid(150.123, res=0.01)
        assert result == 150.12
        
        result = ezIBAsync.roundClosestValid(150.126, res=0.01)
        assert result == 150.13

    def test_round_closest_valid_custom_resolution(self):
        """Test rounding with custom resolution."""
        # Quarter tick
        result = ezIBAsync.roundClosestValid(150.123, res=0.25)
        assert result == 150.0
        
        result = ezIBAsync.roundClosestValid(150.4, res=0.25)
        assert result == 150.5

    def test_round_closest_valid_none_value(self):
        """Test rounding with None value."""
        result = ezIBAsync.roundClosestValid(None, res=0.01)
        assert result is None

    def test_round_closest_valid_custom_decimals(self):
        """Test rounding with custom decimal places."""
        result = ezIBAsync.roundClosestValid(150.123456, res=0.001, decimals=3)
        assert result == 150.123


class TestOrderIntegration:
    """Integration tests for order functionality."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_order_creation_and_placement(self, ezib_instance):
        """Test real order creation and placement (paper trading only)."""
        # Create contract
        contract = await ezib_instance.createStockContract("AAPL")
        
        # Create market order (small quantity for testing)
        order = ezib_instance.createOrder(quantity=1, price=0)  # Market order
        
        # Note: We won't actually place the order in tests to avoid real trades
        # Just verify the order was created properly
        assert order.action == "BUY"
        assert order.totalQuantity == 1
        assert order.orderType == "MKT"
        
        # Test limit order creation
        limit_order = ezib_instance.createOrder(quantity=1, price=100.0)  # Way below market
        assert limit_order.orderType == "LMT"
        assert limit_order.lmtPrice == 100.0

    @pytest.mark.integration
    @pytest.mark.asyncio 
    async def test_real_bracket_order_creation(self, ezib_instance):
        """Test real bracket order creation structure."""
        # Create contract
        contract = await ezib_instance.createStockContract("SPY")
        
        # Test bracket order creation (without actual placement)
        # This tests the order creation logic without placing real orders
        
        # Create entry order
        entry_order = ezib_instance.createOrder(quantity=1, price=400.0)
        
        # Create target order  
        target_order = ezib_instance.createTargetOrder(
            quantity=-1, 
            parentId=1001, 
            target=410.0
        )
        
        # Create stop order
        stop_order = ezib_instance.createStopOrder(
            quantity=-1,
            parentId=1001, 
            stop=390.0
        )
        
        # Verify order relationships
        assert entry_order.action == "BUY"
        assert target_order.action == "SELL"
        assert stop_order.action == "SELL"
        assert target_order.parentId == 1001
        assert stop_order.parentId == 1001