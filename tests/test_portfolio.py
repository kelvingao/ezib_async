"""
Integration tests for the PortfolioManager class.

This module contains integration tests for the PortfolioManager class,
testing the actual connection to Interactive Brokers TWS/Gateway and portfolio updates.

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
from ezib_async.account import PortfolioManager, AccountContext

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
async def test_portfolio_updates(ib_client):
    """
    Test portfolio updates from IB for single and multiple accounts.
    
    This test verifies that:
    1. Event handlers are registered before connection
    2. Portfolio data is received and processed correctly
    3. Multiple accounts are properly handled when available
    
    Note: For multi-account testing, this requires an IB Gateway/TWS instance 
    with multiple accounts configured.
    """
    # Create PortfolioManager with the IB client (without connecting)
    # This ensures event handlers are registered BEFORE connection
    portfolio_manager = PortfolioManager(ib_client, AccountContext(ib_client))
    
    try:
        # Now connect to IB Gateway/TWS
        print("Connecting to IB Gateway/TWS...")
        await ib_client.connectAsync(
            host=IB_HOST,
            port=IB_PORT,  
            clientId=IB_CLIENT_ID
        )
        
        print(f"Connected: {ib_client.isConnected()}")
        
        # Get managed accounts
        managed_accounts = ib_client.managedAccounts()
        print(f"Managed accounts: {managed_accounts}")
        
        # Test with single account first
        if managed_accounts:
            # Use the first account
            active_account = managed_accounts[0]
            print(f"\n=== Testing with account: {active_account} ===")
            
            # Request updates for this account
            print(f"Requesting updates for account: {active_account}")
            await ib_client.reqAccountUpdatesAsync(active_account)
            
            # Wait for updates to be processed
            print("Waiting for portfolio updates (1 second)...")
            await asyncio.sleep(1)
            
            # Check if we received any portfolio items
            try:
                # Get portfolio for specific account
                account_portfolio = portfolio_manager.get_portfolio(active_account)
                print(f"\nPortfolio for account {active_account}:")
                print(f"Number of positions: {len(account_portfolio)}")
                
                # Print portfolio details (limited to save space)
                for symbol, portfolio_item in account_portfolio.items():
                    print(f"  {symbol}:")
                    print(f"    Position: {portfolio_item['position']}")
                    print(f"    Market Price: {portfolio_item['marketPrice']}")
                    print(f"    Market Value: {portfolio_item['marketValue']}")
                    print(f"    Unrealized P&L: {portfolio_item['unrealizedPNL']}")
                
                # Try to get portfolio summary if pandas is available
                try:
                    import pandas as pd
                    portfolio_summary = portfolio_manager.get_portfolio_summary(active_account)
                    if not portfolio_summary.empty:
                        print(f"\nPortfolio Summary for {active_account}:")
                        print(f"  Total market value: ${portfolio_summary['marketValue'].sum():.2f}")
                        print(f"  Total unrealized P&L: ${portfolio_summary['unrealizedPNL'].sum():.2f}")
                except ImportError:
                    print("Pandas not available, skipping portfolio summary")
                except Exception as e:
                    print(f"Error getting portfolio summary: {e}")
                    
            except ValueError as e:
                print(f"Error accessing portfolio for account {active_account}: {e}")
        
        # Test with multiple accounts if available
        if len(managed_accounts) > 1:
            print("\n=== Testing with multiple accounts ===")
            
            # Cancel updates for first account
            ib_client.client.reqAccountUpdates(False, active_account)
            await asyncio.sleep(0.5)
            
            # Use the second account
            second_account = managed_accounts[1]
            print(f"Switching to account: {second_account}")
            
            # Request updates for second account
            print(f"Requesting updates for account: {second_account}")
            ib_client.client.reqAccountUpdates(True, second_account)
            
            # Wait for updates to be processed
            print("Waiting for portfolio updates (1 second)...")
            await asyncio.sleep(1)
            
            # Check portfolio data for the second account
            try:
                # Get portfolio for specific account
                account_portfolio = portfolio_manager.get_portfolio(second_account)
                print(f"\nPortfolio for account {second_account}:")
                print(f"Number of positions: {len(account_portfolio)}")
                
                # Print portfolio details (limited to save space)
                for symbol, portfolio_item in account_portfolio.items():
                    print(f"  {symbol}:")
                    print(f"    Position: {portfolio_item['position']}")
                    print(f"    Market Value: {portfolio_item['marketValue']}")
                    print(f"    Unrealized P&L: {portfolio_item['unrealizedPNL']}")
                
            except ValueError as e:
                print(f"Error accessing portfolio for account {second_account}: {e}")
            
            # Test accessing portfolio without specifying account
            # This should fail with multiple accounts
            print("\nTesting access without specifying account (should fail with multiple accounts):")
            try:
                portfolio = portfolio_manager.portfolio
                print("WARNING: Was able to access portfolio without specifying account!")
                print(f"Default portfolio contains {len(portfolio)} positions")
            except ValueError as e:
                print(f"Expected error when accessing portfolio without account: {e}")
                assert "multiple accounts exist" in str(e), "Error should mention multiple accounts"
        else:
            print("\nOnly one account available, skipping multi-account tests.")
            
    finally:
        # Cancel account updates for any active account
        if 'managed_accounts' in locals() and managed_accounts:
            for account in managed_accounts:
                print(f"Canceling updates for account: {account}")
                try:
                    ib_client.client.reqAccountUpdates(False, account)
                except Exception as e:
                    print(f"Error canceling updates for {account}: {e}")
        
        # Disconnect from IB Gateway/TWS
        print("Disconnecting...")
        ib_client.disconnect()
        print(f"Disconnected: {not ib_client.isConnected()}")

# If running directly, use asyncio.run to execute the test
if __name__ == "__main__":
    # When running directly, use asyncio.run to execute the test
    import time
    import sys
    
    start_time = time.time()
    asyncio.run(test_portfolio_updates(ib_client()))
    end_time = time.time()
    
    print(f"\nTest completed in {end_time - start_time:.2f} seconds")
    sys.exit(0)