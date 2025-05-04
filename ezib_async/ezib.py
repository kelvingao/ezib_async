"""
Asynchronous Interactive Brokers API client.

This module provides a high-level, Pythonic interface to the Interactive Brokers API,
using ib_async for asynchronous execution and event handling.
"""

import asyncio
import sys
import logging

from ib_async import IB
from ezib_async import util

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
        self.connected = False
        
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
        ibhost = ibhost or self._ibhost
        ibport = ibport or self._ibport
        ibclient = ibclient or self._ibclient
        
        # Update default account if provided
        if account is not None:
            self._default_account = account
            self._logger.info(f"Default account set to {account}")
        
        # Log connection attempt
        self._logger.info(f"Connecting to IB at {ibhost}:{ibport} (client ID: {ibclient})")
        
        try:
            # Connect using the IB client
            await self.ib.connectAsync(host=ibhost, port=ibport, clientId=ibclient)
            
            # Update connection state
            self.connected = self.ib.isConnected()
            self._logger.info("Connected to IB successfully")
            return True
                
        except Exception as e:
            self._logger.error(f"Error connecting to IB: {e}")
            self.connected = False
            return False

    # ---------------------------------------
    def disconnect(self):
        """
        Synchronous disconnect method.
        """
        if self.ib.isConnected():
            self._logger.info("Disconnecting from ezIBAsync")
            self.ib.disconnect()
            self.connected = False

if __name__ == "__main__":
    util.logToConsole(logging.INFO)
    logging.getLogger("ib_async").setLevel(logging.WARNING)
    ezib = ezIBAsync()
    asyncio.run(ezib.connectAsync())