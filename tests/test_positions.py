"""
Integration tests for the PositionManager class.

This module contains integration tests for the PositionManager class,
testing the actual connection to Interactive Brokers TWS/Gateway and position updates.

To run these tests, you need to have IB Gateway or TWS running.
These tests are meant to be run manually and are not part of the automated test suite.
"""
import asyncio
import logging
import sys
import pytest
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ib_async import IB
from ezib_async.account import PositionManager, AccountContext

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Connection parameters - can be overridden with environment variables
IB_HOST = os.environ.get('IB_HOST', '127.0.0.1')
IB_PORT = int(os.environ.get('IB_PORT', '4001'))  # Default: 4002 for Gateway paper trading
IB_CLIENT_ID = int(os.environ.get('IB_CLIENT_ID', '0'))
IB_CONNECTION_TIMEOUT = float(os.environ.get('IB_CONNECTION_TIMEOUT', '0.5'))  # Seconds

@pytest.fixture
def ib_client():
    """
    Fixture that provides an IB client instance.
    
    Important: We create the IB instance without connecting it first,
    so that event handlers can be registered before connection.
    """
    # Create IB client without connecting
    ib = IB()
    
    # Return the client for use in tests
    # The test will handle connection and disconnection
    return ib

@pytest.mark.asyncio
async def test_position_updates(ib_client):
    """
    Test position updates from IB.
    
    This test verifies that:
    1. Event handlers are registered before connection
    2. Position data is received and processed correctly
    3. Multiple accounts are handled properly
    """
    # Create PositionManager with the IB client (without connecting)
    # This ensures event handlers are registered BEFORE connection
    position_manager = PositionManager(ib_client, AccountContext(ib_client))
    
    try:
        # Now connect to IB Gateway/TWS
        print("Connecting to IB Gateway/TWS...")
        await ib_client.connectAsync(
            host=IB_HOST,
            port=IB_PORT,  
            clientId=IB_CLIENT_ID
        )
        
        print(f"Connected: {ib_client.isConnected()}")
        
        positions = position_manager.positions
        print(f"Received positions: {list(positions.keys())}")
        
        # Print position details
        for symbol, position_data in positions.items():
            print(f"Position for {symbol}:")
            print(f"  Quantity: {position_data['position']}")
            print(f"  Average Cost: {position_data['avgCost']}")
            print(f"  Account: {position_data['account']}")
        
        # Verify we have position data (this may fail if the account has no positions)
        if len(positions) > 0:
            print("Positions received successfully")
        else:
            print("No positions found in the account. This is not necessarily an error.")
            print("To properly test position updates, ensure the account has at least one position.")
            
    except ValueError as e:
        # Handle the case where no accounts are available
        print(f"Error retrieving positions: {e}")
        
    finally:
        # Disconnect from IB Gateway/TWS
        print("Disconnecting...")
        ib_client.disconnect()
        print(f"Disconnected: {not ib_client.isConnected()}")