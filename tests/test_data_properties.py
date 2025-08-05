#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for data properties functionality in ezIBAsync.

Tests auto-updating properties for account, positions, portfolio, and market data access.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pandas import DataFrame

from ezib_async import ezIBAsync
# Import helper functions from conftest directly
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from conftest import create_mock_account_value, create_mock_position, create_mock_portfolio_item


class TestAccountProperties:
    """Test account-related properties."""

    def test_accounts_property(self):
        """Test accounts property returns all accounts."""
        ezib = ezIBAsync()
        
        # Setup test data
        ezib._accounts = {
            "DU123456": {"NetLiquidation": "100000", "BuyingPower": "50000"},
            "DU789012": {"NetLiquidation": "200000", "BuyingPower": "100000"}
        }
        
        # Execute
        result = ezib.accounts
        
        # Verify
        assert result == ezib._accounts
        assert len(result) == 2
        assert "DU123456" in result
        assert "DU789012" in result

    def test_account_codes_property(self):
        """Test accountCodes property returns list of account codes."""
        ezib = ezIBAsync()
        
        # Setup test data
        ezib._accounts = {
            "DU123456": {"NetLiquidation": "100000"},
            "DU789012": {"NetLiquidation": "200000"},
            "DU345678": {"NetLiquidation": "300000"}
        }
        
        # Execute
        result = ezib.accountCodes
        
        # Verify
        expected = ["DU123456", "DU789012", "DU345678"]
        assert result == expected
        assert len(result) == 3

    def test_account_property_default_account(self):
        """Test account property returns default account."""
        ezib = ezIBAsync()
        ezib._default_account = "DU123456"
        
        # Setup test data
        test_account_data = {"NetLiquidation": "100000", "BuyingPower": "50000"}
        ezib._accounts = {"DU123456": test_account_data}
        
        with patch.object(ezib, 'getAccount', return_value=test_account_data) as mock_get:
            # Execute
            result = ezib.account
            
            # Verify
            mock_get.assert_called_once()
            assert result == test_account_data

    def test_get_account_default(self):
        """Test getAccount with default account."""
        ezib = ezIBAsync()
        ezib._default_account = "DU123456"
        
        # Setup test data
        test_data = {"NetLiquidation": "100000"}
        ezib._accounts = {"DU123456": test_data}
        
        # Execute
        result = ezib.getAccount()
        
        # Verify
        assert result == test_data

    def test_get_account_specific(self):
        """Test getAccount with specific account."""
        ezib = ezIBAsync()
        
        # Setup test data
        ezib._accounts = {
            "DU123456": {"NetLiquidation": "100000"},
            "DU789012": {"NetLiquidation": "200000"}
        }
        
        # Execute
        result = ezib.getAccount("DU789012")
        
        # Verify
        assert result == {"NetLiquidation": "200000"}

    def test_get_account_empty_accounts(self):
        """Test getAccount when no accounts exist."""
        ezib = ezIBAsync()
        ezib._accounts = {}
        
        # Execute
        result = ezib.getAccount()
        
        # Verify
        assert result == {}

    def test_get_account_not_found(self):
        """Test getAccount with non-existent account."""
        ezib = ezIBAsync()
        ezib._default_account = "DU123456"  # Set default account
        ezib._accounts = {"DU123456": {"NetLiquidation": "100000"}}
        
        # Execute - should return default account when requested account not found
        result = ezib.getAccount("DU999999")
        
        # Verify returns default account data (actual implementation behavior)
        assert result == {"NetLiquidation": "100000"}

    def test_get_account_multiple_accounts_no_default(self):
        """Test getAccount with multiple accounts but no account specified."""
        ezib = ezIBAsync()
        ezib._default_account = None
        ezib._accounts = {
            "DU123456": {"NetLiquidation": "100000"},
            "DU789012": {"NetLiquidation": "200000"}
        }
        
        # Execute and verify exception
        with pytest.raises(ValueError, match="Must specify account number"):
            ezib.getAccount()

    def test_get_active_account_default(self):
        """Test _get_active_account with default account."""
        ezib = ezIBAsync()
        ezib._default_account = "DU123456"
        
        # Execute
        result = ezib._get_active_account()
        
        # Verify
        assert result == "DU123456"

    def test_get_active_account_specified(self):
        """Test _get_active_account with specified account."""
        ezib = ezIBAsync()
        ezib._accounts = {"DU789012": {}}
        
        # Execute
        result = ezib._get_active_account("DU789012")
        
        # Verify
        assert result == "DU789012"

    def test_get_active_account_not_found(self):
        """Test _get_active_account with non-existent account."""
        ezib = ezIBAsync()
        ezib._accounts = {"DU123456": {}}
        
        # Execute
        result = ezib._get_active_account("DU999999")
        
        # Verify
        assert result is None


class TestPositionProperties:
    """Test position-related properties."""

    def test_positions_property(self):
        """Test positions property returns all positions."""
        ezib = ezIBAsync()
        
        # Setup test data
        test_positions = {
            "DU123456": {
                "AAPL": {"symbol": "AAPL", "position": 100, "avgCost": 150.0}
            }
        }
        ezib._positions = test_positions
        
        # Execute
        result = ezib.positions
        
        # Verify
        assert result == test_positions

    def test_position_property_default_account(self):
        """Test position property returns default account positions."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'getPosition', return_value={"AAPL": {}}) as mock_get:
            # Execute
            result = ezib.position
            
            # Verify
            mock_get.assert_called_once()
            assert result == {"AAPL": {}}

    def test_get_position_default_account(self):
        """Test getPosition with default account."""
        ezib = ezIBAsync()
        ezib._default_account = "DU123456"
        
        # Setup test data
        test_positions = {"AAPL": {"position": 100}}
        ezib._positions = {"DU123456": test_positions}
        
        # Execute
        result = ezib.getPosition()
        
        # Verify
        assert result == test_positions

    def test_get_position_specific_account(self):
        """Test getPosition with specific account."""
        ezib = ezIBAsync()
        
        # Setup test data
        ezib._accounts = {"DU123456": {}, "DU789012": {}}  # Set up accounts first
        ezib._positions = {
            "DU123456": {"AAPL": {"position": 100}},
            "DU789012": {"MSFT": {"position": 200}}
        }
        
        # Execute
        result = ezib.getPosition("DU789012")
        
        # Verify
        assert result == {"MSFT": {"position": 200}}

    def test_get_position_empty_positions(self):
        """Test getPosition when no positions exist."""
        ezib = ezIBAsync()
        ezib._positions = {}
        
        # Execute
        result = ezib.getPosition()
        
        # Verify
        assert result == {}

    def test_get_position_account_not_found(self):
        """Test getPosition with non-existent account."""
        ezib = ezIBAsync()
        ezib._accounts = {"DU123456": {}}  # Set up known accounts
        ezib._positions = {"DU123456": {}}
        
        # Execute - should return empty dict when account not found
        result = ezib.getPosition("DU999999")
        
        # Verify returns empty dict (consistent with getAccount behavior)  
        assert result == {}

    def test_get_position_multiple_accounts_no_default(self):
        """Test getPosition with multiple accounts but no account specified."""
        ezib = ezIBAsync()
        ezib._default_account = None
        ezib._positions = {
            "DU123456": {"AAPL": {}},
            "DU789012": {"MSFT": {}}
        }
        
        # Execute and verify exception
        with pytest.raises(ValueError, match="Must specify account number"):
            ezib.getPosition()


class TestPortfolioProperties:
    """Test portfolio-related properties."""

    def test_portfolios_property(self):
        """Test portfolios property returns all portfolios."""
        ezib = ezIBAsync()
        
        # Setup test data
        test_portfolios = {
            "DU123456": {
                "AAPL": {"symbol": "AAPL", "marketValue": 15000.0}
            }
        }
        ezib._portfolios = test_portfolios
        
        # Execute
        result = ezib.portfolios
        
        # Verify
        assert result == test_portfolios

    def test_portfolio_property_default_account(self):
        """Test portfolio property returns default account portfolio."""
        ezib = ezIBAsync()
        
        with patch.object(ezib, 'getPortfolio', return_value={"AAPL": {}}) as mock_get:
            # Execute
            result = ezib.portfolio
            
            # Verify
            mock_get.assert_called_once()
            assert result == {"AAPL": {}}

    def test_get_portfolio_default_account(self):
        """Test getPortfolio with default account."""
        ezib = ezIBAsync()
        ezib._default_account = "DU123456"
        
        # Setup test data
        test_portfolio = {"AAPL": {"marketValue": 15000.0}}
        ezib._portfolios = {"DU123456": test_portfolio}
        
        # Execute
        result = ezib.getPortfolio()
        
        # Verify
        assert result == test_portfolio

    def test_get_portfolio_specific_account(self):
        """Test getPortfolio with specific account."""
        ezib = ezIBAsync()
        
        # Setup test data
        ezib._accounts = {"DU123456": {}, "DU789012": {}}  # Set up accounts first
        ezib._portfolios = {
            "DU123456": {"AAPL": {"marketValue": 15000.0}},
            "DU789012": {"MSFT": {"marketValue": 30000.0}}
        }
        
        # Execute
        result = ezib.getPortfolio("DU789012")
        
        # Verify
        assert result == {"MSFT": {"marketValue": 30000.0}}

    def test_get_portfolio_empty_portfolios(self):
        """Test getPortfolio when no portfolios exist."""
        ezib = ezIBAsync()
        ezib._portfolios = {}
        
        # Execute
        result = ezib.getPortfolio()
        
        # Verify
        assert result == {}

    def test_get_portfolio_account_not_found(self):
        """Test getPortfolio with non-existent account."""
        ezib = ezIBAsync()
        ezib._accounts = {"DU123456": {}}  # Set up known accounts
        ezib._portfolios = {"DU123456": {}}
        
        # Execute - should return empty list when account not found (see getPortfolio implementation)
        result = ezib.getPortfolio("DU999999")
        
        # Verify returns empty list (based on getPortfolio implementation)
        assert result == []

    def test_get_portfolio_no_default_account(self):
        """Test getPortfolio with no default account specified."""
        ezib = ezIBAsync()
        ezib._default_account = None
        ezib._portfolios = {"DU123456": {}}
        
        # Execute
        result = ezib.getPortfolio()
        
        # Verify returns empty list when no default account
        assert result == []


class TestMarketDataProperties:
    """Test market data properties."""

    def test_market_data_property_initialization(self):
        """Test marketData property is properly initialized."""
        ezib = ezIBAsync()
        
        # Execute
        result = ezib.marketData
        
        # Verify
        assert isinstance(result, dict)
        assert 0 in result  # Default ticker ID
        assert isinstance(result[0], DataFrame)

    def test_market_data_property_access(self):
        """Test accessing market data after updates."""
        ezib = ezIBAsync()
        
        # Setup test data
        test_df = DataFrame({"bid": [150.0], "ask": [150.5], "last": [150.25]})
        ezib.marketData[1] = test_df
        
        # Execute
        result = ezib.marketData
        
        # Verify
        assert 1 in result
        assert result[1].equals(test_df)

    def test_market_depth_data_property_initialization(self):
        """Test marketDepthData property is properly initialized.""" 
        ezib = ezIBAsync()
        
        # Execute
        result = ezib.marketDepthData
        
        # Verify
        assert isinstance(result, dict)
        assert 0 in result  # Default ticker ID
        assert isinstance(result[0], DataFrame)

    def test_market_depth_data_property_access(self):
        """Test accessing market depth data after updates."""
        ezib = ezIBAsync()
        
        # Setup test data
        test_df = DataFrame({
            "bid": [150.0, 149.9],
            "ask": [150.1, 150.2],
            "bidsize": [100, 200], 
            "asksize": [150, 250]
        })
        ezib.marketDepthData[1] = test_df
        
        # Execute
        result = ezib.marketDepthData
        
        # Verify
        assert 1 in result
        assert result[1].equals(test_df)

    def test_options_data_property_initialization(self):
        """Test optionsData property is properly initialized."""
        ezib = ezIBAsync()
        
        # Execute
        result = ezib.optionsData
        
        # Verify
        assert isinstance(result, dict)
        assert 0 in result  # Default ticker ID
        assert isinstance(result[0], DataFrame)

    def test_options_data_property_access(self):
        """Test accessing options data after updates."""
        ezib = ezIBAsync()
        
        # Setup test data - simplified options data
        test_df = DataFrame({
            "bid": [5.0], 
            "ask": [5.5], 
            "last": [5.25],
            "iv": [0.25],
            "delta": [0.5]
        })
        ezib.optionsData[1] = test_df
        
        # Execute
        result = ezib.optionsData
        
        # Verify
        assert 1 in result
        assert result[1].equals(test_df)


class TestDataConsistency:
    """Test data consistency across properties."""

    def test_account_data_consistency_after_updates(self):
        """Test account data remains consistent after multiple updates."""
        ezib = ezIBAsync()
        
        # Simulate multiple account value updates
        account_values = [
            create_mock_account_value("NetLiquidation", "100000", account="DU123456"),
            create_mock_account_value("BuyingPower", "50000", account="DU123456"),
            create_mock_account_value("NetLiquidation", "150000", account="DU789012")
        ]
        
        for av in account_values:
            ezib._onAccountValueHandler(av)
        
        # Verify consistency
        accounts = ezib.accounts
        assert len(accounts) == 2
        assert accounts["DU123456"]["NetLiquidation"] == "100000"
        assert accounts["DU123456"]["BuyingPower"] == "50000"
        assert accounts["DU789012"]["NetLiquidation"] == "150000"
        
        # Verify account codes
        account_codes = ezib.accountCodes
        assert "DU123456" in account_codes
        assert "DU789012" in account_codes

    @pytest.mark.asyncio
    async def test_position_data_consistency_after_updates(self):
        """Test position data remains consistent after multiple updates."""
        ezib = ezIBAsync()
        
        # Simulate position updates
        positions = [
            create_mock_position("AAPL", 100, 150.0, "DU123456"),
            create_mock_position("MSFT", 200, 300.0, "DU123456"),
            create_mock_position("GOOGL", 50, 2500.0, "DU789012")
        ]
        
        with patch.object(ezib, 'contractString') as mock_contract_str:
            with patch.object(ezib, 'registerContract', return_value=AsyncMock()) as mock_register:
                # Mock contract string returns
                mock_contract_str.side_effect = ["AAPL", "MSFT", "GOOGL"]
                
                for pos in positions:
                    ezib._onPositionUpdateHandler(pos)
                
                # Give async tasks time to complete
                await asyncio.sleep(0.01)
        
        # Verify consistency
        all_positions = ezib.positions
        assert len(all_positions) == 2  # Two accounts
        assert len(all_positions["DU123456"]) == 2  # Two positions in first account
        assert len(all_positions["DU789012"]) == 1  # One position in second account
        
        # Set up accounts for getPosition to work
        ezib._accounts = {"DU123456": {}, "DU789012": {}}
        
        # Test specific account access
        du123_positions = ezib.getPosition("DU123456")
        assert "AAPL" in du123_positions
        assert "MSFT" in du123_positions
        assert du123_positions["AAPL"]["position"] == 100

    def test_portfolio_data_consistency_after_updates(self):
        """Test portfolio data remains consistent after multiple updates."""
        ezib = ezIBAsync()
        
        # Simulate portfolio updates
        portfolio_items = [
            create_mock_portfolio_item("AAPL", 100, 150.0, 15000.0, 145.0, 500.0, 0.0, "DU123456"),
            create_mock_portfolio_item("MSFT", 200, 300.0, 60000.0, 295.0, 1000.0, 200.0, "DU123456")
        ]
        
        with patch.object(ezib, 'contractString') as mock_contract_str:
            mock_contract_str.side_effect = ["AAPL", "MSFT"]
            
            for item in portfolio_items:
                ezib._onPortfolioUpdateHandler(item)
        
        # Verify consistency
        all_portfolios = ezib.portfolios
        assert len(all_portfolios) == 1
        assert len(all_portfolios["DU123456"]) == 2
        
        # Test total P&L calculations
        aapl_item = all_portfolios["DU123456"]["AAPL"]
        assert aapl_item["totalPNL"] == 500.0  # 500 + 0
        
        msft_item = all_portfolios["DU123456"]["MSFT"]
        assert msft_item["totalPNL"] == 1200.0  # 1000 + 200

    def test_market_data_structures_remain_separate(self):
        """Test that different market data structures remain separate."""
        ezib = ezIBAsync()
        
        # Add data to different structures
        stock_data = DataFrame({"bid": [150.0], "ask": [150.5]})
        options_data = DataFrame({"bid": [5.0], "ask": [5.5], "iv": [0.25]})
        depth_data = DataFrame({"bid": [150.0, 149.9], "ask": [150.1, 150.2]})
        
        ezib.marketData[1] = stock_data
        ezib.optionsData[2] = options_data
        ezib.marketDepthData[3] = depth_data
        
        # Verify structures remain separate
        assert 1 in ezib.marketData and 1 not in ezib.optionsData
        assert 2 in ezib.optionsData and 2 not in ezib.marketData
        assert 3 in ezib.marketDepthData and 3 not in ezib.marketData
        
        # Verify data integrity
        assert ezib.marketData[1].equals(stock_data)
        assert ezib.optionsData[2].equals(options_data)
        assert ezib.marketDepthData[3].equals(depth_data)


class TestPropertyPerformance:
    """Test property access performance and efficiency."""

    def test_property_access_does_not_copy_data(self):
        """Test that property access returns references, not copies."""
        ezib = ezIBAsync()
        
        # Setup test data
        original_accounts = {"DU123456": {"NetLiquidation": "100000"}}
        ezib._accounts = original_accounts
        
        # Access property
        accounts = ezib.accounts
        
        # Modify through property reference
        accounts["DU123456"]["BuyingPower"] = "50000"
        
        # Verify original data was modified (confirming it's a reference)
        assert ezib._accounts["DU123456"]["BuyingPower"] == "50000"

    def test_multiple_property_accesses_consistent(self):
        """Test multiple accesses to same property return consistent data."""
        ezib = ezIBAsync()
        
        # Setup test data
        ezib._accounts = {"DU123456": {"NetLiquidation": "100000"}}
        
        # Multiple accesses
        accounts1 = ezib.accounts
        accounts2 = ezib.accounts
        
        # Verify consistency
        assert accounts1 is accounts2  # Same object reference
        assert accounts1 == accounts2  # Same data

    def test_property_access_with_empty_data(self):
        """Test property access works correctly with empty data structures."""
        ezib = ezIBAsync()
        
        # Clear default data
        ezib._accounts = {}
        ezib._positions = {}
        ezib._portfolios = {}
        
        # Access properties
        accounts = ezib.accounts
        positions = ezib.positions
        portfolios = ezib.portfolios
        
        # Verify empty but valid structures
        assert accounts == {}
        assert positions == {}
        assert portfolios == {}
        assert isinstance(accounts, dict)
        assert isinstance(positions, dict)
        assert isinstance(portfolios, dict)