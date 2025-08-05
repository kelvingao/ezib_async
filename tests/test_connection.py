#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit and integration tests for connection management in ezIBAsync.

Tests connection, disconnection, reconnection, and parameter validation.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch

from ezib_async import ezIBAsync


class TestConnectionManagement:
    """Test connection management functionality."""

    @pytest.mark.asyncio
    async def test_connect_async_success(self, mock_ezib):
        """Test successful connection."""
        # Setup
        mock_ezib.connectAsync = AsyncMock(return_value=True)
        mock_ezib.connected = False
        
        # Execute
        result = await mock_ezib.connectAsync(ibhost="localhost", ibport=4001, ibclient=999)
        
        # Verify
        assert result is True
        mock_ezib.connectAsync.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_async_failure(self, mock_ezib):
        """Test connection failure handling."""
        # Setup - Mock connection failure
        mock_ezib.connectAsync = AsyncMock(side_effect=Exception("Connection failed"))
        mock_ezib.connected = False
        
        # Execute and Verify
        with pytest.raises(Exception, match="Connection failed"):
            await mock_ezib.connectAsync()
        
        assert mock_ezib.connected is False

    @pytest.mark.asyncio
    async def test_connect_async_with_parameters(self):
        """Test connection with custom parameters."""
        # Create real instance for parameter testing
        ezib = ezIBAsync(ibhost="127.0.0.1", ibport=4002, ibclient=888)
        
        # Mock the underlying IB connection
        with patch.object(ezib, 'ib') as mock_ib:
            mock_ib.connectAsync = AsyncMock(return_value=True)
            mock_ib.isConnected = Mock(return_value=True)
            # Mock the accountCodes property by setting _accounts
            ezib._accounts = {"DU123456": {}}
            
            # Execute
            await ezib.connectAsync(ibhost="192.168.1.1", ibport=7497, ibclient=777)
            
            # Verify parameters were updated
            assert ezib._ibhost == "192.168.1.1"
            assert ezib._ibport == 7497
            assert ezib._ibclient == 777
            
            # Verify IB connection called with new parameters
            mock_ib.connectAsync.assert_called_once_with(
                host="192.168.1.1", port=7497, clientId=777, account=None
            )

    @pytest.mark.asyncio
    async def test_connect_async_already_connected(self):
        """Test connecting when already connected."""
        # Create real instance
        ezib = ezIBAsync()
        ezib.connected = True
        
        with patch.object(ezib, 'ib') as mock_ib:
            mock_ib.connectAsync = AsyncMock()
            
            # Execute
            await ezib.connectAsync()
            
            # Verify no additional connection attempt
            mock_ib.connectAsync.assert_not_called()

    def test_disconnect(self):
        """Test disconnection."""
        # Create real instance
        ezib = ezIBAsync()
        ezib.connected = True
        ezib._default_account = "DU123456"
        
        with patch.object(ezib, 'ib') as mock_ib:
            mock_ib.client = Mock()
            mock_ib.client.reqAccountUpdates = Mock()
            mock_ib.disconnect = Mock()
            
            # Execute
            ezib.disconnect()
            
            # Verify disconnection sequence
            mock_ib.client.reqAccountUpdates.assert_called_once_with(False, "DU123456")
            mock_ib.disconnect.assert_called_once()
            assert ezib.connected is False
            assert ezib._disconnected_by_user is True

    def test_disconnect_error_handling(self):
        """Test disconnect with error handling."""
        # Create real instance
        ezib = ezIBAsync()
        ezib.connected = True
        ezib._default_account = "DU123456"
        
        with patch.object(ezib, 'ib') as mock_ib:
            # Mock error during disconnect
            mock_ib.client = Mock()
            mock_ib.client.reqAccountUpdates = Mock(side_effect=Exception("Disconnect error"))
            mock_ib.disconnect = Mock()
            
            # Execute - should not raise exception
            ezib.disconnect()
            
            # Verify error was handled gracefully
            assert ezib._disconnected_by_user is True

    @pytest.mark.asyncio
    async def test_reconnect_success(self):
        """Test successful reconnection."""
        # Create real instance
        ezib = ezIBAsync(ibhost="localhost", ibport=4001, ibclient=999)
        ezib.connected = False
        ezib._disconnected_by_user = False
        
        with patch.object(ezib, 'connectAsync') as mock_connect:
            # Setup side effect to simulate successful connection on second attempt
            def connect_side_effect(*args, **kwargs):
                if mock_connect.call_count == 2:  # Second call succeeds
                    ezib.connected = True
                return None
            
            mock_connect.side_effect = connect_side_effect
            
            # Execute
            await ezib._reconnect(reconnect_interval=0.01, max_attempts=5)
            
            # Verify reconnection attempts (should be 2: first fails, second succeeds)
            assert mock_connect.call_count == 2
            assert ezib.connected is True

    @pytest.mark.asyncio
    async def test_reconnect_max_attempts_exceeded(self):
        """Test reconnection failure after max attempts."""
        # Create real instance
        ezib = ezIBAsync(ibhost="localhost", ibport=4001, ibclient=999)
        ezib.connected = False
        ezib._disconnected_by_user = False
        
        with patch.object(ezib, 'connectAsync') as mock_connect:
            # Mock all attempts fail
            mock_connect.return_value = AsyncMock(return_value=None)
            
            # Execute
            await ezib._reconnect(reconnect_interval=0.01, max_attempts=3)
            
            # Verify all attempts were made
            assert mock_connect.call_count == 3
            assert ezib.connected is False

    @pytest.mark.asyncio
    async def test_reconnect_user_disconnected(self):
        """Test reconnection skipped when user disconnected."""
        # Create real instance
        ezib = ezIBAsync()
        ezib.connected = False
        ezib._disconnected_by_user = True
        
        with patch.object(ezib, 'connectAsync') as mock_connect:
            # Execute
            await ezib._reconnect(reconnect_interval=0.01, max_attempts=3)
            
            # Verify no reconnection attempts
            mock_connect.assert_not_called()

    def test_on_disconnected_handler(self):
        """Test disconnection event handler."""
        # Create real instance
        ezib = ezIBAsync()
        ezib.connected = True
        ezib._disconnected_by_user = False
        
        with patch.object(ezib, '_reconnect') as mock_reconnect:
            with patch('asyncio.create_task') as mock_create_task:
                # Execute
                ezib._onDisconnectedHandler()
                
                # Verify disconnection handling
                assert ezib.connected is False
                mock_create_task.assert_called_once()

    def test_on_disconnected_handler_user_initiated(self):
        """Test disconnection handler when user initiated."""
        # Create real instance
        ezib = ezIBAsync()
        ezib.connected = True
        ezib._disconnected_by_user = True
        
        with patch.object(ezib, '_reconnect') as mock_reconnect:
            with patch('asyncio.create_task') as mock_create_task:
                # Execute
                ezib._onDisconnectedHandler()
                
                # Verify no reconnection attempt
                assert ezib.connected is False
                mock_create_task.assert_not_called()


class TestConnectionIntegration:
    """Integration tests for connection management."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_connection_success(self):
        """Test real connection to IB Gateway/TWS."""
        ezib = ezIBAsync(ibhost='localhost', ibport=4001, ibclient=999)
        
        try:
            # Attempt connection
            await ezib.connectAsync()
            
            if not ezib.connected:
                pytest.skip("Could not connect to IB Gateway/TWS. Ensure it's running on port 4001.")
            
            # Verify connection state
            assert ezib.connected is True
            assert ezib._ibhost == 'localhost'
            assert ezib._ibport == 4001
            assert ezib._ibclient == 999
            
            # Verify account codes are available
            assert len(ezib.accountCodes) > 0
            
        finally:
            # Always disconnect
            if ezib.connected:
                ezib.disconnect()
                assert ezib.connected is False

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_with_invalid_port(self):
        """Test connection failure with invalid port."""
        ezib = ezIBAsync(ibhost='localhost', ibport=9999, ibclient=999)
        
        try:
            # Attempt connection to invalid port
            await ezib.connectAsync()
            
            # Should fail to connect
            assert ezib.connected is False
            
        finally:
            # Ensure cleanup
            if ezib.connected:
                ezib.disconnect()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_client_connections(self):
        """Test multiple client connections with different IDs."""
        ezib1 = ezIBAsync(ibhost='localhost', ibport=4001, ibclient=998)
        ezib2 = ezIBAsync(ibhost='localhost', ibport=4001, ibclient=997)
        
        try:
            # Connect both clients
            await ezib1.connectAsync()
            await ezib2.connectAsync()
            
            if not (ezib1.connected and ezib2.connected):
                pytest.skip("Could not connect both clients to IB Gateway/TWS.")
            
            # Verify both are connected with different client IDs
            assert ezib1.connected is True
            assert ezib2.connected is True
            assert ezib1._ibclient != ezib2._ibclient
            
        finally:
            # Disconnect both clients
            if ezib1.connected:
                ezib1.disconnect()
            if ezib2.connected:
                ezib2.disconnect()