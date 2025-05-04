"""
Asynchronous Interactive Brokers API client.

This module provides a high-level, Pythonic interface to the Interactive Brokers API,
using ib_async for asynchronous execution and event handling.
"""

import asyncio
import sys
import logging

from ib_async import IB

# Check Python version
if sys.version_info < (3, 11):
    raise SystemError("ezIBAsync requires Python version >= 3.11")

class ezIBAsync:
    """
    Asynchronous Interactive Brokers API client.
    
    This class provides a high-level interface to the IB API with async support,
    managing connections, accounts, positions, portfolios, contracts, and orders.
    """
    
    def __init__(self, ibhost='127.0.0.1', ibport=4001, 
                 ibclient=1, account=None):
        """
        Initialize the ezIBAsync client.
        
        Args:
            ibhost (str): Host address for IB connection
            ibport (int): Port number for IB connection
            ibclient (int): Client ID for IB connection
            account (str, optional): Default account to use
        """
        # Store connection parameters
        self._ibhost = ibhost
        self._ibport = ibport
        self._ibclient = ibclient
        self._default_account = account

        self._logger = logging.getLogger('ezib_async.ezib')

        # Initialize the IB client directly
        self.ib = IB()
        self.isConnected = False
        self._disconnected_by_user = False

        self._register_events_handlers()

    # ---------------------------------------
    async def connectAsync(self, ibhost=None, ibport=None, 
                          ibclient=None, account=None):
        """
        Connect to the Interactive Brokers TWS/Gateway asynchronously.
        
        Args:
            ibhost (str, optional): Host address for IB connection
            ibport (int, optional): Port number for IB connection
            ibclient (int, optional): Client ID for IB connection
            account (str, optional): Default account to use
        """
        # Use provided parameters or fall back to stored values
        self._ibhost = ibhost or self._ibhost
        self._ibport = ibport or self._ibport
        self._ibclient = ibclient or self._ibclient
        
        # Update default account if provided
        if account is not None:
            self._default_account = account
            self._logger.info(f"Default account set to {account}")
        
        try:
            # Connect using the IB client
            self._logger.info(f"Connecting to IB at {self._ibhost}:{self._ibport} (client ID: {self._ibclient})")
            await self.ib.connectAsync(host=self._ibhost, port=self._ibport, clientId=self._ibclient)
            
            # Update connection state
            self.isConnected = self.ib.isConnected()
            self._logger.info("Connected to IB successfully")
            self._disconnected_by_user = False
            return True
                
        except Exception as e:
            self._logger.error(f"Error connecting to IB: {e}")
            self.isConnected = False
            return False

    # ---------------------------------------
    def _register_events_handlers(self):
        """
        Registers event handlers for the Interactive Brokers TWS/Gateway connection.
        
        """
        if self.ib is not None:
            # Register disconnection handler
            self.ib.disconnectedEvent += self._on_disconnected
            self._logger.debug("Disconnection Event handler registered")

    # ---------------------------------------
    def _on_disconnected(self):
        """
        Disconnection event handler for Interactive Brokers TWS/Gateway.
        
        """
        self.isConnected = False

        if not self._disconnected_by_user:
            self._logger.warning("Disconnected from IB")
            asyncio.create_task(self._reconnect())

    async def _reconnect(self, reconnect_interval = 2, max_attempts=300):
        """
        Reconnects to Interactive Brokers TWS/Gateway after a disconnection.
        
        """
        attempt = 0
        while not self.isConnected and attempt < max_attempts and not self._disconnected_by_user:
            attempt += 1
            self._logger.info(f"Reconnection attempt {attempt}/{max_attempts}...")
            
            try:
                await asyncio.sleep(reconnect_interval)
                await self.connectAsync(ibhost=self._ibhost, ibport=self._ibport, ibclient=self._ibclient)
                
                if self.isConnected:
                    self._logger.info("Reconnection successful")
                    break
            except Exception as e:
                self._logger.error(f"Reconnection failed: {e}")
                
        if not self.isConnected and attempt >= max_attempts:
            self._logger.error(f"Failed to reconnect after {max_attempts} attempts, giving up")

    # ---------------------------------------
    def disconnect(self):
        """
        Disconnects from the Interactive Brokers API (TWS/Gateway) and cleans up resources.

        """
        self._disconnected_by_user = True
        if self.isConnected:
            self._logger.info("Disconnecting from IB")
            self.ib.disconnect()
            self.isConnected = False