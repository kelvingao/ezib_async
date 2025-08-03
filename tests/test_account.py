"""
Integration tests for the AccountManager class.

This module contains integration tests for the AccountManager class,
testing the actual connection to Interactive Brokers TWS/Gateway and account updates.

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
from ezib_async.account import AccountContext

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
async def test_account_value_updates(ib_client):
    """
    Test account value updates from IB.
    
    This test verifies that:
    1. Event handlers are registered before connection
    2. Account values are received and processed correctly
    """
    # Create AccountContext with the IB client (without connecting)
    # This ensures event handlers are registered BEFORE connection
    account_context = AccountContext(ib_client, 'U9860850')
    
    try:
        # Now connect to IB Gateway/TWS
        print("Connecting to IB Gateway/TWS...")
        await ib_client.connectAsync(
            host=IB_HOST,
            port=IB_PORT,  
            clientId=IB_CLIENT_ID
        )

        await account_context.initialize()

        # account_context.set_default_account('U13792768')
        
        print(f"Connected: {ib_client.isConnected()}")
        
        # Wait for initial account updates to be processed
        # IB automatically sends account updates on connection for single accounts
        print("Waiting for account updates (0.5 seconds)...")
        # await asyncio.sleep(0.5)
        
        # Check if we received any account values
        accounts = account_context._accounts
        print(f"Received accounts: {list(accounts.keys())}")
        
        # Verify we have at least one account
        assert len(accounts) > 0, "No accounts received"
        
        # Get the first account
        first_account = list(accounts.keys())[0]
        account_values = accounts[first_account]
        
        # Print some account values for verification
        print(f"Account values for {first_account}:")
        for key, value in list(account_values.items())[:10]:  # Show first 10 values
            print(f"  {key}: {value}")
        
        # Verify we have some account values
        assert len(account_values) > 0, "No account values received"
        print(f"Total account values found: {len(account_values)}")
        
        # Check for common account values
        common_values = ['NetLiquidation', 'TotalCashValue', 'AvailableFunds']
        found_values = [value for value in common_values if value in account_values]
        print(f"Found common values: {found_values}")
        
    finally:
        # Cancel account updates for the active account
        if 'managed_accounts' in locals() and managed_accounts:
            active_account = managed_accounts[0]
            print(f"Canceling updates for account: {active_account}")
            try:
                await ib_client.reqAccountUpdatesAsync(False, active_account)
            except Exception as e:
                print(f"Error canceling updates: {e}")
            
        # Disconnect from IB Gateway/TWS
        print("Disconnecting...")
        ib_client.disconnect()
        print(f"Disconnected: {not ib_client.isConnected()}")

@pytest.mark.asyncio
async def test_account_summary_updates(ib_client):
    """
    Test account summary updates from IB.
    
    This test verifies that:
    1. Event handlers for account summary are registered before connection
    2. Account summary values are received and processed correctly through _handle_account_summary
    """
    # Create AccountContext with the IB client (without connecting)
    # This ensures event handlers are registered BEFORE connection
    account_context = AccountContext(ib_client)
    
    try:
        # Now connect to IB Gateway/TWS
        print("Connecting to IB Gateway/TWS...")
        await ib_client.connectAsync(
            host=IB_HOST,
            port=IB_PORT,  
            clientId=IB_CLIENT_ID
        )
        
        print(f"Connected: {ib_client.isConnected()}")
        
        # Request account summary explicitly
        print("Requesting account summary...")
        # The reqAccountSummary method takes a reqId, groupName, and tags
        # summary_tags = 'NetLiquidation,TotalCashValue,AvailableFunds,GrossPositionValue,BuyingPower'
        summary_tags = (
            "AccountType,NetLiquidation,TotalCashValue,SettledCash,"
            "AccruedCash,BuyingPower,EquityWithLoanValue,"
            "PreviousDayEquityWithLoanValue,GrossPositionValue,RegTEquity,"
            "RegTMargin,SMA,InitMarginReq,MaintMarginReq,AvailableFunds,"
            "ExcessLiquidity,Cushion,FullInitMarginReq,FullMaintMarginReq,"
            "FullAvailableFunds,FullExcessLiquidity,LookAheadNextChange,"
            "LookAheadInitMarginReq,LookAheadMaintMarginReq,"
            "LookAheadAvailableFunds,LookAheadExcessLiquidity,"
            "HighestSeverity,DayTradesRemaining,DayTradesRemainingT+1,"
            "DayTradesRemainingT+2,DayTradesRemainingT+3,"
            "DayTradesRemainingT+4,Leverage,$LEDGER:ALL"
        )
        # await ib_client.reqAccountSummaryAsync()
        
        # Wait for account summary updates to be processed
        print("Waiting for account summary updates (0.2 seconds)...")
        await asyncio.sleep(0.2)
        
        # Check if we received any account values
        accounts = account_context._accounts
        print(f"Received accounts: {list(accounts.keys())}")
        
        # Verify we have at least one account
        assert len(accounts) > 0, "No accounts received"
        
        # Display account summary for each account
        for account_id in accounts.keys():
            account_values = accounts[account_id]
            
            # Print account summary values for verification
            print(f"\nAccount summary values for {account_id}:")
            requested_tags = summary_tags.split(',')
            found_tags = 0
            for tag in requested_tags:
                if tag in account_values:
                    print(f"  {tag}: {account_values[tag]}")
                    found_tags += 1
            
            print(f"Total account summary values found for {account_id}: {found_tags} out of {len(requested_tags)} requested")
            
            # Check for common account values
            common_values = ['NetLiquidation', 'TotalCashValue', 'AvailableFunds']
            found_values = [value for value in common_values if value in account_values]
            print(f"Found common values for {account_id}: {found_values}")
        
    finally:
        # Cancel account updates for the active account
        if 'managed_accounts' in locals() and managed_accounts:
            active_account = managed_accounts[0]
            print(f"Canceling updates for account: {active_account}")
            try:
                ib_client.client.reqAccountUpdates(False, active_account)
            except Exception as e:
                print(f"Error canceling updates: {e}")
            
        # Disconnect from IB Gateway/TWS
        print("Disconnecting...")
        ib_client.disconnect()
        print(f"Disconnected: {not ib_client.isConnected()}")



# If running directly, use asyncio.run to execute the test
if __name__ == "__main__":
    # When running directly, use asyncio.run to execute the test
    asyncio.run(test_account_value_updates(ib_client()))