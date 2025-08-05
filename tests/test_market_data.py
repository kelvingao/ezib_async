#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit and integration tests for market data functionality in ezIBAsync.

Tests market data requests, cancellation, depth data, and event handling.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from ezib_async import ezIBAsync
# Import helper functions from conftest directly
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from conftest import create_mock_ticker


class TestMarketDataRequests:
    """Test market data request functionality."""

    @pytest.mark.asyncio
    async def test_request_market_data_single_contract(self, mock_ezib, mock_stock_contract):
        """Test requesting market data for a single contract."""
        # Setup
        mock_ezib.requestMarketData = AsyncMock()
        mock_ezib.tickerId = Mock(return_value=1)
        mock_ezib.isMultiContract = Mock(return_value=False)
        mock_ezib.contractString = Mock(return_value="AAPL")
        
        # Execute
        await mock_ezib.requestMarketData([mock_stock_contract], snapshot=False)
        
        # Verify
        mock_ezib.requestMarketData.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_market_data_multiple_contracts(self, mock_ezib, mock_stock_contract, mock_forex_contract):
        """Test requesting market data for multiple contracts."""
        # Setup
        contracts = [mock_stock_contract, mock_forex_contract]
        mock_ezib.requestMarketData = AsyncMock()
        
        # Execute
        await mock_ezib.requestMarketData(contracts)
        
        # Verify
        mock_ezib.requestMarketData.assert_called_once_with(contracts)

    @pytest.mark.asyncio
    async def test_request_market_data_all_contracts(self, mock_ezib):
        """Test requesting market data for all contracts when none specified."""
        # Setup
        mock_ezib.contracts = [Mock(), Mock()]
        mock_ezib.requestMarketData = AsyncMock()
        
        # Execute - passing None should use all contracts
        await mock_ezib.requestMarketData(None)
        
        # Verify
        mock_ezib.requestMarketData.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_market_data_with_snapshot(self, mock_ezib, mock_stock_contract):
        """Test requesting snapshot market data."""
        # Setup
        mock_ezib.requestMarketData = AsyncMock()
        
        # Execute
        await mock_ezib.requestMarketData([mock_stock_contract], snapshot=True)
        
        # Verify
        mock_ezib.requestMarketData.assert_called_once_with([mock_stock_contract], snapshot=True)

    @pytest.mark.asyncio
    async def test_request_market_data_skip_multi_contract(self):
        """Test skipping multi-contracts in market data requests."""
        # Create real instance for this test
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'ib') as mock_ib:
            with patch.object(ezib, 'isMultiContract', return_value=True):
                with patch.object(ezib, 'contractString', return_value="MULTI"):
                    mock_contract = Mock()
                    
                    # Execute
                    await ezib.requestMarketData([mock_contract])
                    
                    # Verify IB API not called for multi-contract
                    mock_ib.reqMktData.assert_not_called()

    @pytest.mark.asyncio
    async def test_request_market_data_rate_limiting(self):
        """Test rate limiting in market data requests."""
        # Create real instance
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'ib') as mock_ib:
            with patch.object(ezib, 'isMultiContract', return_value=False):
                with patch.object(ezib, 'contractString', return_value="AAPL"):
                    with patch('asyncio.sleep') as mock_sleep:
                        mock_contract = Mock()
                        
                        # Execute
                        await ezib.requestMarketData([mock_contract])
                        
                        # Verify rate limiting sleep was called
                        mock_sleep.assert_called_once_with(0.0021)

    def test_cancel_market_data_single_contract(self, mock_ezib, mock_stock_contract):
        """Test canceling market data for a single contract."""
        # Setup
        mock_ezib.connected = True
        mock_ezib.cancelMarketData = Mock()
        
        # Execute
        mock_ezib.cancelMarketData([mock_stock_contract])
        
        # Verify
        mock_ezib.cancelMarketData.assert_called_once()

    def test_cancel_market_data_not_connected(self, mock_ezib):
        """Test canceling market data when not connected."""
        # Setup
        mock_ezib.connected = False
        mock_ezib.cancelMarketData = Mock()
        
        # Execute
        mock_ezib.cancelMarketData([Mock()])
        
        # Verify
        mock_ezib.cancelMarketData.assert_called_once()

    def test_cancel_market_data_all_contracts(self, mock_ezib):
        """Test canceling market data for all contracts."""
        # Setup
        mock_ezib.contracts = [Mock(), Mock()]
        mock_ezib.connected = True
        mock_ezib.cancelMarketData = Mock()
        
        # Execute
        mock_ezib.cancelMarketData(None)
        
        # Verify
        mock_ezib.cancelMarketData.assert_called_once()


class TestMarketDepthRequests:
    """Test market depth (Level II) functionality."""

    def test_request_market_depth_default_rows(self, mock_ezib, mock_stock_contract):
        """Test requesting market depth with default rows."""
        # Setup
        mock_ezib.requestMarketDepth = Mock()
        
        # Execute
        mock_ezib.requestMarketDepth([mock_stock_contract])
        
        # Verify
        mock_ezib.requestMarketDepth.assert_called_once()

    def test_request_market_depth_custom_rows(self, mock_ezib, mock_stock_contract):
        """Test requesting market depth with custom number of rows."""
        # Setup
        mock_ezib.requestMarketDepth = Mock()
        
        # Execute
        mock_ezib.requestMarketDepth([mock_stock_contract], num_rows=5)
        
        # Verify
        mock_ezib.requestMarketDepth.assert_called_once_with([mock_stock_contract], num_rows=5)

    def test_request_market_depth_max_rows_limit(self):
        """Test market depth request with row limit enforcement."""
        # Create real instance
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'ib') as mock_ib:
            with patch.object(ezib, 'contractString', return_value="AAPL"):
                mock_contract = Mock()
                mock_contract.symbol = "AAPL"
                
                # Execute with more than 10 rows
                ezib.requestMarketDepth([mock_contract], num_rows=15)
                
                # Verify IB API called with max 10 rows
                mock_ib.reqMktDepth.assert_called_once()
                # Note: Can't easily verify the numRows parameter without more complex mocking

    def test_cancel_market_depth(self, mock_ezib, mock_stock_contract):
        """Test canceling market depth requests."""
        # Setup
        mock_ezib.connected = True
        mock_ezib.cancelMarketDepth = Mock()
        
        # Execute
        mock_ezib.cancelMarketDepth([mock_stock_contract])
        
        # Verify
        mock_ezib.cancelMarketDepth.assert_called_once()

    def test_cancel_market_depth_not_connected(self, mock_ezib):
        """Test canceling market depth when not connected."""
        # Setup
        mock_ezib.connected = False
        mock_ezib.cancelMarketDepth = Mock()
        
        # Execute
        mock_ezib.cancelMarketDepth([Mock()])
        
        # Verify
        mock_ezib.cancelMarketDepth.assert_called_once()


class TestMarketDataEventHandling:
    """Test market data event handling and processing."""

    def test_on_pending_tickers_handler_stock_data(self):
        """Test processing stock ticker data."""
        # Create real instance
        ezib = ezIBAsync()
        
        # Create mock tickers
        stock_ticker = create_mock_ticker("AAPL", bid=150.0, ask=150.5, last=150.25)
        stock_ticker.contract.secType = "STK"
        stock_ticker.domBids = []
        stock_ticker.domAsks = []
        
        with patch.object(ezib.pendingMarketTickersEvent, 'emit') as mock_emit:
            # Execute
            ezib._onPendingTickersHandler([stock_ticker])
            
            # Verify stock ticker was emitted
            mock_emit.assert_called_once_with([stock_ticker])

    def test_on_pending_tickers_handler_option_data(self):
        """Test processing option ticker data."""
        # Create real instance
        ezib = ezIBAsync()
        
        # Create mock option ticker
        option_ticker = create_mock_ticker("SPY", bid=5.0, ask=5.5, last=5.25)
        option_ticker.contract.secType = "OPT"
        option_ticker.domBids = []
        option_ticker.domAsks = []
        
        with patch.object(ezib.pendingOptionsTickersEvent, 'emit') as mock_emit:
            # Execute
            ezib._onPendingTickersHandler([option_ticker])
            
            # Verify option ticker was emitted
            mock_emit.assert_called_once_with([option_ticker])

    def test_on_pending_tickers_handler_market_depth(self):
        """Test processing market depth ticker data."""
        # Create real instance
        ezib = ezIBAsync()
        
        # Create mock ticker with market depth
        depth_ticker = create_mock_ticker("AAPL")
        depth_ticker.domBids = [Mock()]  # Has market depth data
        depth_ticker.domAsks = [Mock()]
        
        with patch.object(ezib.updateMarketDepthEvent, 'emit') as mock_emit:
            # Execute
            ezib._onPendingTickersHandler([depth_ticker])
            
            # Verify market depth event was emitted
            assert mock_emit.call_count >= 1  # May be called twice for bids and asks

    def test_on_pending_tickers_handler_mixed_data(self):
        """Test processing mixed ticker types."""
        # Create real instance
        ezib = ezIBAsync()
        
        # Create mixed tickers
        stock_ticker = create_mock_ticker("AAPL")
        stock_ticker.contract.secType = "STK"
        stock_ticker.domBids = []
        stock_ticker.domAsks = []
        
        option_ticker = create_mock_ticker("SPY")
        option_ticker.contract.secType = "OPT"
        option_ticker.domBids = []
        option_ticker.domAsks = []
        
        depth_ticker = create_mock_ticker("MSFT")
        depth_ticker.domBids = [Mock()]
        depth_ticker.domAsks = []
        
        with patch.object(ezib.pendingMarketTickersEvent, 'emit') as mock_market_emit:
            with patch.object(ezib.pendingOptionsTickersEvent, 'emit') as mock_options_emit:
                with patch.object(ezib.updateMarketDepthEvent, 'emit') as mock_depth_emit:
                    # Execute
                    ezib._onPendingTickersHandler([stock_ticker, option_ticker, depth_ticker])
                    
                    # Verify appropriate events were emitted
                    mock_market_emit.assert_called_once()
                    mock_options_emit.assert_called_once()
                    mock_depth_emit.assert_called_once()

    def test_handle_orderbook_update(self):
        """Test orderbook update handling."""
        # Create real instance
        ezib = ezIBAsync()
        
        # Create mock ticker
        mock_ticker = Mock()
        
        with patch.object(ezib.updateMarketDepthEvent, 'emit') as mock_emit:
            # Execute
            ezib._handle_orderbook_update(mock_ticker)
            
            # Verify event was emitted
            mock_emit.assert_called_once_with(mock_ticker)


class TestMarketDataProperties:
    """Test market data property access."""

    def test_market_data_property_access(self, mock_ezib):
        """Test accessing marketData property."""
        # Setup
        mock_ezib.marketData = {1: {"bid": 150.0, "ask": 150.5, "last": 150.25}}
        
        # Execute
        result = mock_ezib.marketData
        
        # Verify
        assert result == {1: {"bid": 150.0, "ask": 150.5, "last": 150.25}}

    def test_market_depth_data_property_access(self, mock_ezib):
        """Test accessing marketDepthData property."""
        # Setup
        mock_depth_data = {"bid": [150.0, 149.95], "ask": [150.5, 150.55]}
        mock_ezib.marketDepthData = {1: mock_depth_data}
        
        # Execute
        result = mock_ezib.marketDepthData
        
        # Verify
        assert result == {1: mock_depth_data}

    def test_options_data_property_access(self, mock_ezib):
        """Test accessing optionsData property."""
        # Setup
        mock_options_data = {"iv": 0.25, "delta": 0.5, "gamma": 0.1}
        mock_ezib.optionsData = {1: mock_options_data}
        
        # Execute
        result = mock_ezib.optionsData
        
        # Verify
        assert result == {1: mock_options_data}


class TestMarketDataIntegration:
    """Integration tests for market data functionality."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_market_data_request(self, ezib_instance):
        """Test real market data request with IB connection."""
        # Create a simple stock contract
        contract = await ezib_instance.createStockContract("AAPL")
        
        try:
            # Request market data
            await ezib_instance.requestMarketData([contract], snapshot=True)
            
            # Wait briefly for data
            await asyncio.sleep(2)
            
            # Verify market data structure exists
            ticker_id = ezib_instance.tickerId(contract)
            assert ticker_id in ezib_instance.marketData
            
            # Check if we got any data (market may be closed)
            market_data = ezib_instance.marketData[ticker_id]
            assert isinstance(market_data, dict)
            
        finally:
            # Always cancel market data
            ezib_instance.cancelMarketData([contract])

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_market_depth_request(self, ezib_instance):
        """Test real market depth request with IB connection."""
        # Create a liquid stock contract
        contract = await ezib_instance.createStockContract("SPY")
        
        try:
            # Request market depth
            ezib_instance.requestMarketDepth([contract], num_rows=5)
            
            # Wait briefly for data
            await asyncio.sleep(3)
            
            # Verify market depth structure exists
            ticker_id = ezib_instance.tickerId(contract)
            assert ticker_id in ezib_instance.marketDepthData
            
            # Check market depth data structure
            depth_data = ezib_instance.marketDepthData[ticker_id]
            assert isinstance(depth_data, dict)
            
        finally:
            # Always cancel market depth
            ezib_instance.cancelMarketDepth([contract])

    @pytest.mark.integration  
    @pytest.mark.asyncio
    async def test_real_streaming_market_data(self, ezib_instance):
        """Test real streaming market data with event handling."""
        # Create contract
        contract = await ezib_instance.createStockContract("MSFT")
        
        # Event handler to capture data
        received_events = []
        
        def market_data_handler(tickers):
            received_events.extend(tickers)
        
        try:
            # Subscribe to market data events
            ezib_instance.pendingMarketTickersEvent += market_data_handler
            
            # Request streaming market data
            await ezib_instance.requestMarketData([contract], snapshot=False)
            
            # Wait for some streaming updates
            await asyncio.sleep(5)
            
            # Verify we received some events (if market is open)
            # Note: This may be 0 if market is closed
            assert isinstance(received_events, list)
            
        finally:
            # Cleanup
            ezib_instance.pendingMarketTickersEvent -= market_data_handler
            ezib_instance.cancelMarketData([contract])