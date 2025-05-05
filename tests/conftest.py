#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Common test fixtures for both unit tests and integration tests.
"""
import pytest
import pytest_asyncio

from ezib_async import ezIBAsync

# Connection parameters
IB_HOST = 'localhost'
IB_PORT = 4001
IB_CLIENT_ID = 999

def pytest_addoption(parser):
    """Add custom command line options for pytest."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require a running IB Gateway/TWS"
    )

def pytest_configure(config):
    config.option.asyncio_default_fixture_loop_scope = "function"

@pytest_asyncio.fixture
async def ezib_instance():
    """
    Fixture that provides a connected ezIBAsync instance.
    
    This fixture can be used by any test that needs a connected IB client.
    It will automatically handle connection and disconnection.
    """
    # Create ezIBAsync instance
    ezib = ezIBAsync(ibhost=IB_HOST, ibport=IB_PORT, ibclient=IB_CLIENT_ID)
    
    try:
        # Connect to IB Gateway/TWS
        connected = await ezib.connectAsync()
        
        if not connected or not ezib.isConnected:
            pytest.skip("Could not connect to IB Gateway/TWS. Skipping integration test.")
        
        # Return the connected instance
        yield ezib
        
    finally:
        # Disconnect when done
        if ezib and hasattr(ezib, 'isConnected') and ezib.isConnected:
            ezib.disconnect()