"""
Integration tests for the ConnectionManager class.

This module contains integration tests for the ConnectionManager class,
testing the actual connection to Interactive Brokers TWS/Gateway.

To run these tests, you need to have IB Gateway or TWS running.
These tests are meant to be run manually and are not part of the automated test suite.
"""
import asyncio
import pytest

from ezib_async import ezIBAsync

# Connection parameters
IB_HOST = 'localhost'
IB_PORT = 4001
IB_CLIENT_ID = 999

@pytest.mark.asyncio
async def test_reconnection():
    """Test the automatic reconnection functionality.
    
    Note: This test requires manual intervention to disconnect
    the IB Gateway/TWS while the test is running.
    """
    # Create a connection manager with shorter reconnection interval
    ezib = ezIBAsync(ibhost=IB_HOST, ibport=IB_PORT, ibclient=IB_CLIENT_ID)
    
    try:
        # Connect to IB Gateway/TWS
        print("Connecting to IB Gateway/TWS...")
        await ezib.connectAsync()
        
        print(f"Connected: {ezib.connected}")
        
        # Wait for manual disconnection and reconnection
        print("Please manually restart IB Gateway/TWS to test reconnection...")
        print("Waiting for 120 seconds...")
        for i in range(15):
            await asyncio.sleep(5)
            print(f"Still running... Connection status: {ezib.connected}")
        
    finally:
        # Disconnect from IB Gateway/TWS
        print("Disconnecting...")
        ezib.disconnect()
        print(f"Disconnected: {not ezib.connected}")
