"""
MIT License

Copyright (c) 2025 Kelvin Gao

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sys
import asyncio
import logging

from pandas import DataFrame
from typing import Dict, List
from ib_async import (
    IB,
    AccountValue, Position, PortfolioItem,
    Contract, Stock, Future, Forex, Option, Index,
    ComboLeg, Order
)

from eventkit import Event

# check python version
if sys.version_info < (3, 12):
    raise SystemError("ezIBAsync requires Python version >= 3.12")

class ezIBAsync:
    """
    Asynchronous Interactive Brokers API client.
    
    This class provides a high-level interface to the IB API with async support,
    managing connections, accounts, positions, portfolios, contracts, and orders.
    """
    
    events = (
        "pendingMarketTickersEvent",
        "pendingOptionsTickersEvent",
        "updateMarketDepthEvent"
    )
    
    @staticmethod
    def roundClosestValid(val, res = 0.01, decimals = None):
        """
        Round to closest valid resolution.
        
        Args:
            val: Value to round
            res: Resolution to round to
            decimals: Number of decimal places
            
        Returns:
            Rounded value
        """
        if val is None:
            return None
            
        # Handle invalid resolution values
        if res == 0 or not isinstance(res, (int, float)):
            return val
            
        if decimals is None and "." in str(res):
            decimals = len(str(res).split('.')[1])
            
        return round(round(val / res) * res, decimals)
    
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
        self._createEvents()

        # store connection parameters
        self._ibhost = ibhost
        self._ibport = ibport
        self._ibclient = ibclient
        self._default_account = account
        
        # auto-construct for every contract/order
        self.tickerIds: Dict[int, str] = {0: "SYMBOL"}
        self.contracts: List[Contract] = []
        self.orders: Dict[int, Order] = {}
        self.account_orders: Dict[str, Dict[int, Order]] = {}
        self.account_symbols_orders: Dict[str, Dict[str, List[Order]]] = {}
        self.symbol_orders: Dict[str, List[Order]] = {}

        # accounts
        self._accounts: Dict[str, List[AccountValue]] = {}  # accountId -> accountValues
        self._positions: Dict[str, Dict[str, Position]] = {}
        self._portfolios: Dict[str, Dict[str, PortfolioItem]] = {}  # accountId -> contractString -> portfolioItem
        self._contract_details: List[dict] = []  # multiple expiry/strike/side contracts

        self.contract_details: Dict[str, dict] = {}
        self.localSymbolExpiry: Dict[str, str] = {}

        self._logger = logging.getLogger('ezib_async.ezib')

        # holds market data
        tickDF = DataFrame({
            "datetime": [0], "bid": [0], "bidsize": [0],
            "ask": [0], "asksize": [0], "last": [0], "lastsize": [0]
        })
        tickDF.set_index('datetime', inplace=True)
        self.marketData: Dict[int, DataFrame] = {0: tickDF}  # idx = tickerId

        # holds orderbook data
        l2DF = DataFrame(index=range(5), data={
            "bid": 0, "bidsize": 0,
            "ask": 0, "asksize": 0
        })
        self.marketDepthData: Dict[int, DataFrame] = {0: l2DF}  # idx = tickerId

        # holds options data
        optionsDF = DataFrame({
            "datetime": [0], "oi": [0], "volume": [0], "underlying": [0], "iv": [0],
            "bid": [0], "bidsize": [0], "ask": [0], "asksize": [0], "last": [0], "lastsize": [0],
            # opt field
            "price": [0], "dividend": [0], "imp_vol": [0], "delta": [0],
            "gamma": [0], "vega": [0], "theta": [0],
            "last_price": [0], "last_dividend": [0], "last_imp_vol": [0], "last_delta": [0],
            "last_gamma": [0], "last_vega": [0], "last_theta": [0],
            "bid_price": [0], "bid_dividend": [0], "bid_imp_vol": [0], "bid_delta": [0],
            "bid_gamma": [0], "bid_vega": [0], "bid_theta": [0],
            "ask_price": [0], "ask_dividend": [0], "ask_imp_vol": [0], "ask_delta": [0],
            "ask_gamma": [0], "ask_vega": [0], "ask_theta": [0],
        })
        optionsDF.set_index('datetime', inplace=True)
        self.optionsData: Dict[int, DataFrame] = {0: optionsDF}  # idx = tickerId

        # Initialize the IB client directly
        self.ib = IB()
        self.connected = False
        self._disconnected_by_user = False

        self._setup_handlers()

    def _createEvents(self):

        self.pendingMarketTickersEvent = Event("pendingMarketTickersEvent")
        self.pendingOptionsTickersEvent = Event("pendingOptionsTickersEvent")
        self.updateMarketDepthEvent = Event("updateMarketDepthEvent")

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
        self._ibhost = ibhost if ibhost is not None else self._ibhost
        self._ibport = ibport if ibport is not None else self._ibport
        self._ibclient = ibclient if ibclient is not None else self._ibclient
        self._default_account = account if account is not None else self._default_account
        
        try:
            # Connect using the IB client
            if self.connected:
                return

            self._logger.info(f"Connecting to IB at {self._ibhost}:{self._ibport} (client ID: {self._ibclient})")
            await self.ib.connectAsync(host=self._ibhost, port=self._ibport, clientId=self._ibclient, account=self._default_account)
            
            # Update connection state
            self.connected = self.ib.isConnected()
            self._logger.info("Connected to IB successfully")
            self._disconnected_by_user = False

            # Validate default account
            if self._default_account is not None:
                if self._default_account not in self.accountCodes:
                    self._logger.warning(f"Default account {self._default_account} not found in available accounts: {self.accountCodes}")
                    # Switch to first available account
                    self._default_account = self.accountCodes[0]
                    self._logger.warning(f"Switched default account to {self._default_account}")
            else:
                self._default_account = self.accountCodes[0]
                self.ib.client.reqAccountUpdates(True, self._default_account)
                
        except Exception as e:
            self._logger.error(f"Error connecting to IB: {e}")
            self.connected = False
            return False

    # ---------------------------------------
    def _setup_handlers(self):
        """
        Registers event handlers for the Interactive Brokers TWS/Gateway connection.
        
        """
        if self.ib is not None:
            # disconnection handler
            self.ib.disconnectedEvent += self._onDisconnectedHandler

            # accounts info handlers
            self.ib.accountValueEvent += self._onAccountValueHandler
            self.ib.accountSummaryEvent += self._onAccountSummaryHandler
            self.ib.positionEvent += self._onPositionUpdateHandler
            self.ib.updatePortfolioEvent += self._onPortfolioUpdateHandler

            # market / options / depth data handler
            self.ib.pendingTickersEvent += self._onPendingTickersHandler

    # ---------------------------------------
    async def requestMarketData(self, contracts=None, snapshot=False):
        """
        Register to streaming market data updates.
        
        Args:
            contracts: Contract or list of contracts to request market data for.
                       If None, uses all contracts in self.contracts.
            snapshot: If True, request a snapshot instead of streaming data.
        """
            
        # Use all contracts if none specified
        if contracts is None:
            contracts = self.contracts
        elif not isinstance(contracts, list):
            contracts = [contracts]
            
        for contract in contracts:
            # Skip multi-contracts (they need to be expanded first)
            if self.isMultiContract(contract):
                self._logger.debug(f"Skipping multi-contract: {contract.symbol}")
                continue
                
            try:
                # Get ticker ID for the contract
                contractSring = self.contractString(contract)
                
                # Request market data
                self._logger.info(f"Requesting market data for {contract.symbol} ({contractSring})")
                    
                # Request market data
                self.ib.reqMktData(contract, '', snapshot, False)
                
                # Small delay to avoid overwhelming IB API (max 500 requests/second)
                await asyncio.sleep(0.0021)
                
            except Exception as e:
                self._logger.error(f"Error requesting market data for {contract.symbol}: {e}")
    # ---------------------------------------
    def requestMarketDepth(self, contracts=None, num_rows=10):
        
        if num_rows > 10:
            num_rows = 10

        if contracts == None:
            contracts = self.contracts
        elif not isinstance(contracts, list):
            contracts = [contracts]

        for contract in contracts:
            contractSring = self.contractString(contract)
            self._logger.info(f"Requesting market depth for {contract.symbol} ({contractSring})")

            ticker = self.ib.reqMktDepth(contract, numRows=num_rows)
            # ticker.updateEvent += self._handle_orderbook_update

    # ---------------------------------------
    def cancelMarketDepth(self, contracts=None):
        """
        Cancel streaming market depth for contracts.
        
        Args:
            contracts: Contract or list of contracts to cancel market depth for.
                      If None, cancels for all contracts in self.contracts.
        """
        if not self.connected:
            self._logger.info("Not connected to IB")
            return
            
        # Use all contracts if none specified
        if contracts is None:
            contracts = self.contracts
        elif not isinstance(contracts, list):
            contracts = [contracts]
            
        for contract in contracts:
            try:
                # Skip multi-contracts
                if self.isMultiContract(contract):
                    continue
                
                contractString = self.contractString(contract)
                    
                # Cancel market data
                self._logger.info(f"Canceling depth market data for {contract.symbol} ({contractString})")
                self.ib.cancelMktDepth(contract)
                
            except Exception as e:
                self._logger.error(f"Canceling depth market data for {contract.symbol}: {e}")
            
    def _handle_orderbook_update(self, ticker):
        self._logger.debug(f"Orderbook {ticker} received")
        self.updateMarketDepthEvent.emit(ticker)
            
    # ---------------------------------------
    def cancelMarketData(self, contracts=None):
        """
        Cancel streaming market data for contracts.
        
        Args:
            contracts: Contract or list of contracts to cancel market data for.
                      If None, cancels for all contracts in self.contracts.
        """
        if not self.connected:
            self._logger.info("Not connected to IB")
            return
            
        # Use all contracts if none specified
        if contracts is None:
            contracts = self.contracts
        elif not isinstance(contracts, list):
            contracts = [contracts]
            
        for contract in contracts:
            try:
                # Skip multi-contracts
                if self.isMultiContract(contract):
                    continue
                
                contractString = self.contractString(contract)
                    
                # Cancel market data
                self._logger.info(f"Canceling market data for {contract.symbol} ({contractString})")
                self.ib.cancelMktData(contract)
                
            except Exception as e:
                self._logger.error(f"Error canceling market data for {contract.symbol}: {e}")

    # -----------------------------------------
    # Market data event handlers
    # -----------------------------------------
    def _onPendingTickersHandler(self, tickers):
        """
        Handle consolidated ticker updates from IB.
        
        This single handler processes all types of market data updates (price, size, 
        option computation, etc.) using ib_async's consolidated ticker objects.
        
        Args:
            tickers: List of Ticker objects with updated data
        """

        market_tickers = []
        options_tickers = []
        market_depth_tickers = []

        # Handle None tickers
        if tickers is None:
            return

        for t in tickers:
            # Skip None tickers
            if not t or not hasattr(t, 'contract') or not t.contract:
                continue
            
            if t.domAsks:
                market_depth_tickers.append(t)
            
            if t.domBids:
                market_depth_tickers.append(t)
                
            if t.contract.secType in ("OPT", "FOP"):
                options_tickers.append(t)
            else:
                market_tickers.append(t)
                # contract = t.contract
                # symbol = self.contractString(contract)
                # ticker_id = self.tickerId(symbol)

                # is_option = contract.secType in ("OPT", "FOP")
                # df2use = self.optionsData if is_option else self.marketData

                # # Ensure the ticker exists in our data structure
                # if ticker_id not in df2use:
                #     df2use[ticker_id] = df2use[0].copy()
                    
                # # Update common market data fields
                # for field, attr in COMMON_FIELD_MAPPING.items():
                #     if field == "datetime":
                #         df2use[ticker_id].index = [getattr(t, attr)]
                #     else:
                #         df2use[ticker_id][field] = getattr(t, attr)

                # if is_option:

                #     # Handle open interest field based on contract type
                #     if contract.secType == "OPT":
                #         if contract.right == "C" and hasattr(t, "callOpenInterest"):
                #             df2use[ticker_id]['oi'] = t.callOpenInterest
                #         elif contract.right == "P" and hasattr(t, "putOpenInterest"):
                #             df2use[ticker_id]['oi'] = t.putOpenInterest
                #     elif contract.secType == "FOP" and hasattr(t, "futuresOpenInterest"):
                #         df2use[ticker_id]['oi'] = t.futuresOpenInterest
                    
                #     # Handle implied volatility - prioritize impliedVolatility if available
                #     if hasattr(t, "impliedVolatility") and t.impliedVolatility is not None and t.impliedVolatility < 1e6:
                #         df2use[ticker_id]['iv'] = t.impliedVolatility
                #     elif hasattr(t, "lastGreeks") and hasattr(t.lastGreeks, "impliedVol") and t.lastGreeks.impliedVol is not None:
                #         df2use[ticker_id]['iv'] = t.lastGreeks.impliedVol
                                    
                #     if t.modelGreeks:
                #         for key, attr in OPT_FOP_MODELGREEKS_MAPPING.items():
                #             if hasattr(t.modelGreeks, attr):
                #                 val = getattr(t.modelGreeks, attr)
                #                 if val and val < 1e6:
                #                     df2use[ticker_id][key] = val
                    
                #     if t.lastGreeks:
                #         for key, attr in OPT_FOP_LASTGREEKS_MAPPING.items():
                #             if hasattr(t.lastGreeks, attr):
                #                 val = getattr(t.lastGreeks, attr)
                #                 if val and val < 1e6:
                #                     df2use[ticker_id][key] = val
                    
                #     if t.bidGreeks:
                #         for key, attr in OPT_FOP_BIDGREEKS_MAPPING.items():
                #             if hasattr(t.bidGreeks, attr):
                #                 val = getattr(t.bidGreeks, attr)
                #                 if val and val < 1e6:
                #                     df2use[ticker_id][key] = val

                #     if t.askGreeks:
                #         for key, attr in OPT_FOP_ASKGREEKS_MAPPING.items():
                #             if hasattr(t.askGreeks, attr):
                #                 val = getattr(t.askGreeks, attr)
                #                 if val and val < 1e6:
                #                     df2use[ticker_id][key] = val

        # Always emit events (even with empty lists for testing)
        self.pendingMarketTickersEvent.emit(market_tickers)
        if options_tickers:
            self.pendingOptionsTickersEvent.emit(options_tickers)
        if market_depth_tickers:
            self.updateMarketDepthEvent.emit(market_depth_tickers)
            
            # except Exception as e:
            #     self._logger.error(f"Error handling ticker update for {contract.symbol if hasattr(contract, 'symbol') else 'unknown'}: {e}")

    # ---------------------------------------
    # Accounts handling
    # ---------------------------------------
    def _onAccountValueHandler(self, value):
        """
        Handle account value updates from IB.
        
        Args:
            value: AccountValue object from IB
        """
        try:        
            # Validate account name (don't accept empty accounts)
            if not value.account or not value.account.strip():
                self._logger.warning("Ignoring account value update with empty account name")
                return
                
            # Create account entry if it doesn't exist
            if value.account not in self._accounts:
                self._accounts[value.account] = {}
                
            # Set value
            self._accounts[value.account][value.tag] = value.value
            # self._logger.debug(f"Account value update: {value.account} - {value.tag}: {value.value}")
            
        except Exception as e:
            self._logger.error(f"Error handling account value update: {e}")

    # ---------------------------------------
    def _onAccountSummaryHandler(self, summary):
        """
        Handle account summary updates from IB.
        
        Args:
            summary: AccountSummary object from IB
        """
        try:         
            # Create account entry if it doesn't exist
            if summary.account not in self._accounts_summary:
                self._accounts_summary[summary.account] = []
                
            # Set value
            self._accounts_summary[summary.account].append(summary)
            self._logger.debug(f"Account summary update: {summary.account} - {summary.tag}: {summary.value}")
            
        except Exception as e:
            self._logger.error(f"Error handling account summary update: {e}")

    # ---------------------------------------
    @property
    def accounts(self):
        """
        Get all account information.
        
        """
        return self._accounts

    @property
    def accountsSummary(self):
        """
        Get all account summary information.
        
        """
        return self._accounts_summary

    @property
    def account(self):
        """
        Get information for the default account.
        
        Returns:
            Dictionary of account information

        """
        return self.getAccount()
    
    @property
    def accountCodes(self):
        return list(self._accounts.keys())

    # ---------------------------------------
    def _onDisconnectedHandler(self):
        """
        Disconnection event handler for Interactive Brokers TWS/Gateway.
        
        """
        self.connected = False

        if not self._disconnected_by_user:
            self._logger.warning("Disconnected from IB")
            try:
                asyncio.create_task(self._reconnect())
            except RuntimeError:
                # No event loop running, skip reconnection
                self._logger.debug("No event loop running, skipping automatic reconnection")

    async def _reconnect(self, reconnect_interval = 2, max_attempts=300):
        """
        Reconnects to Interactive Brokers TWS/Gateway after a disconnection.
        
        """
        attempt = 0
        while not self.connected and attempt < max_attempts and not self._disconnected_by_user:
            attempt += 1
            self._logger.info(f"Reconnection attempt {attempt}/{max_attempts}...")
            
            try:
                await asyncio.sleep(reconnect_interval)
                await self.connectAsync(ibhost=self._ibhost, ibport=self._ibport, ibclient=self._ibclient)
                
                if self.connected:
                    self._logger.info("Reconnection successful")
                    break
            except Exception as e:
                self._logger.error(f"Reconnection failed: {e}")
                
        if not self.connected and attempt >= max_attempts:
            self._logger.error(f"Failed to reconnect after {max_attempts} attempts, giving up")

    # ---------------------------------------
    def disconnect(self):
        """
        Disconnects from the Interactive Brokers API (TWS/Gateway) and cleans up resources.

        """
        try:
            # cancel all tasks
            # tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            # [t.cancel() for t in tasks]
            
            # # waiting for close...
            # await asyncio.gather(*tasks, return_exceptions=True)
            
            # disconnect
            self._disconnected_by_user = True
            if self.connected and self.ib:
                self.ib.client.reqAccountUpdates(False, self._default_account)
                self._logger.info("Disconnecting from IB")
                self.ib.disconnect()
                self._logger.info("Disconnected.")
            self.connected = False
        except Exception as e:
            self._logger.error(f"Error during disconnection: {str(e)}")

    # ---------------------------------------
    def getAccount(self, account=None):
        if len(self._accounts) == 0:
            return {}

        account = self._get_active_account(account)

        if account is None:
            if len(self._accounts) > 1:
                raise ValueError("Must specify account number as multiple accounts exists.")
            return self._accounts[self._default_account]

        if account in self._accounts:
            return self._accounts[account]

        raise ValueError("Account %s not found in account list" % account)

    # ---------------------------------------
    def _get_active_account(self, account = None):
        """
        Get the active account to use.

        """
        if account is None:
            return self._default_account

        elif account not in self.accountCodes:
            self._logger.warning(f"'{account}' not found in available accounts: {self.accountCodes}")
            return None
            # raise ValueError("Account %s not found in account list" % account)
            # return None

        # if len(self._accounts) > 1:
            # raise ValueError("Must specify account number as multiple accounts exists.")
            # return self._accounts[list(self._accounts.keys())[0]]
        
        return account

    # =============================================
    # Contracts Managment
    # =============================================


    # -----------------------------------------
    # tickerId/Symbols constructors
    # -----------------------------------------
    def tickerId(self, contract_identifier):
        """
        Get the ticker ID for a contract or symbol.
        
        If the contract or symbol doesn't have a ticker ID yet, a new one is assigned.
        
        Args:
            contract_identifier: Contract object or symbol string
        """
        # Handle contract object
        symbol = contract_identifier
        if isinstance(symbol, (Contract, tuple)):
            symbol = self.contractString(symbol)
            
        # Check if symbol already has a ticker ID
        for tickerId, tickerSymbol in self.tickerIds.items():
            if symbol == tickerSymbol:
                return tickerId
                
        # Assign new ticker ID
        tickerId = len(self.tickerIds)
        self.tickerIds[tickerId] = symbol
        return tickerId
        
    def tickerSymbol(self, tickerId):
        """
        Get the symbol for a ticker ID.

        """
        try:
            return self.tickerIds[tickerId]
        except KeyError:
            return ""

    # ---------------------------------------
    @staticmethod
    def contract_to_tuple(contract):
        """
        Convert a contract object to a tuple representation.
        
        Args:
            contract: Contract object
        """
        return (
            contract.symbol,
            contract.secType,
            contract.exchange,
            contract.currency,
            contract.lastTradeDateOrContractMonth,
            contract.strike,
            contract.right
        )

    def contractString(self, contract, separator = "_"):
        """
        Convert a contract object or tuple to a string representation.
        
        Args:
            contract: Contract object or tuple
            separator: Separator to use between contract elements
            
        Returns:
            String representation of the contract
        """
        contractTuple = contract
        
        try:
            if not isinstance(contract, tuple):
                contractTuple = self.contract_to_tuple(contract)
            if contractTuple[1] in ("OPT", "FOP"):
                # Format strike price for options
                strike = '{:0>5d}'.format(int(contractTuple[5])) + \
                    format(contractTuple[5], '.3f').split('.')[1]
                    
                contractString = (contractTuple[0] + str(contractTuple[4]) +
                                  contractTuple[6][0] + strike, contractTuple[1])
                                  
            elif contractTuple[1] == "FUT":
                # Format expiry for futures
                exp = str(contractTuple[4])[:6]
                month_codes = {
                    1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
                    7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z'
                }
                exp = month_codes[int(exp[4:6])] + exp[:4]
                contractString = (contractTuple[0] + exp, contractTuple[1])
                
            elif contractTuple[1] == "CASH":
                contractString = (contractTuple[0] + contractTuple[3], contractTuple[1])
                
            else:  # STK
                contractString = (contractTuple[0], contractTuple[1])
                
            # Construct string
            contractString = separator.join(
                str(v) for v in contractString).replace(separator + "STK", "")
                
        except Exception as e:
            self._logger.error(f"Error converting contract to string: {e}")
            # Fallback to contract.symbol if available, otherwise str(contract)
            if hasattr(contract, 'symbol'):
                contractString = contract.symbol
            else:
                contractString = str(contract)
            
        return contractString.replace(" ", "_").upper()

    # ---------------------------------------
    def contractDetails(self, contract_identifier):
        """
        Get contract details for a contract, symbol, or ticker ID.
        
        Args:
            contract_identifier: Contract object, symbol string, or ticker ID
            
        Returns:
            Dictionary of contract details
        """
        if isinstance(contract_identifier, Contract):
            tickerId = self.tickerId(contract_identifier)
        else:
            if isinstance(contract_identifier, int) or (
                isinstance(contract_identifier, str) and contract_identifier.isdigit()
            ):
                tickerId = int(contract_identifier)
            else:
                tickerId = self.tickerId(contract_identifier)
                
        # Check if we have the contract details
        if tickerId in self._contract_details:
            return self._contract_details[tickerId]
            
        # Default values if no details are available
        return {
            'tickerId': tickerId,
            'category': None, 
            'contractMonth': '', 
            'downloaded': False, 
            'evMultiplier': 0,
            'evRule': None, 
            'industry': None, 
            'liquidHours': '', 
            'longName': '',
            'marketName': '', 
            'minTick': 0.01, 
            'orderTypes': '', 
            'priceMagnifier': 0,
            'subcategory': None, 
            'timeZoneId': '', 
            'tradingHours': '', 
            'underConId': 0,
            'validExchanges': 'SMART', 
            'contracts': [Contract()], 
            'conId': 0,
            'summary': {
                'conId': 0, 
                'currency': 'USD', 
                'exchange': 'SMART', 
                'lastTradeDateOrContractMonth': '',
                'includeExpired': False, 
                'localSymbol': '', 
                'multiplier': '',
                'primaryExch': None, 
                'right': None, 
                'secType': '',
                'strike': 0.0, 
                'symbol': '', 
                'tradingClass': '',
            }
        }

    # ---------------------------------------
    async def createContract(self, *args, **kwargs):
        """
        Create a contract from a tuple representation or parameters.
        
        Args:
            *args: Contract parameters (symbol, sec_type, exchange, currency, lastTradeDateOrContractMonth, strike, right)
            **kwargs: Additional contract parameters
            
        Returns:
            Created contract object
        """
        try:
            if len(args) == 1 and isinstance(args[0], Contract):
                newContract = args[0]
            else:
                # Create a new Contract object
                newContract = Contract()
                newContract.symbol = args[0]
                newContract.secType = args[1]
                newContract.exchange = args[2] or "SMART"
                newContract.currency = args[3] or "USD"
                newContract.lastTradeDateOrContractMonth = args[4] or ""
                newContract.strike = args[5] or 0.0
                newContract.right = args[6] or ""
                
                if len(args) >= 8:
                    newContract.multiplier = args[7]
                    
                # Include expired contracts for historical data
                newContract.includeExpired = newContract.secType in ("FUT", "OPT", "FOP")
            if "combo_legs" in kwargs:
                newContract.comboLegs = kwargs["combo_legs"]
                
            # qualify this contract
            qualified_contracts = await self.ib.qualifyContractsAsync(newContract)
            
            qualified_contract = qualified_contracts[0] if qualified_contracts else None
            if not qualified_contract:
                self._logger.warning(f'Unknown contract: {newContract}')
                return None

            # contractString = self.contractString(qualified_contract)
            # tickerId = self.tickerId(contractString)
            
            contract = self.getContract(qualified_contract)
            
            if contract:
                self._logger.debug(f"Contract: {qualified_contract} has been registered.")
                return contract

            # Add contract to pool
            self.contracts.append(qualified_contract)

            # Request contract details if not a combo contract
            if "combo_legs" not in kwargs:
                try:
                    await self.requestContractDetails(qualified_contract)
                    # await asyncio.sleep(1.5 if self.isMultiContract(newContract) else 0.5)
                except KeyboardInterrupt:
                    self._logger.warning("Contract details request interrupted")
                    
            return qualified_contract
            
        except (asyncio.TimeoutError, Exception) as e:
            self._logger.error(f"Error creating contract: {e}")
            return None

    # ---------------------------------------
    async def createStockContract(self, symbol, currency = "USD", exchange = "SMART"):
        """
        Create a stock contract.

        """
        contract = Stock(symbol=symbol, exchange=exchange, currency=currency)
        return await self.createContract(contract)
    
    # -----------------------------------------
    async def createFuturesContract(self, symbol, currency = "USD", expiry = None, exchange = "CME", multiplier = ""):
        """
        Create a futures contract.
        
        Args:
            symbol: Futures symbol
            currency: Currency code
            expiry: Expiry date(s) in YYYYMMDD format
            exchange: Exchange code
            multiplier: Contract multiplier

        Returns:
            Futures contract object or list of contracts
        """
        # Handle continuous futures
        if symbol and symbol[0] == "@":
            return await self.createContinuousFuturesContract(symbol[1:], exchange)
            
        # Handle multiple expiries
        expiries = [expiry] if expiry and not isinstance(expiry, list) else expiry
        
        if not expiries:
            contract = Future(symbol=symbol, exchange=exchange, currency=currency, multiplier=multiplier)
            return await self.createContract(contract)
            
        contracts = []
        for fut_expiry in expiries:
            contract = Future(symbol=symbol, lastTradeDateOrContractMonth=fut_expiry, 
                             exchange=exchange, currency=currency, multiplier=multiplier)
            contract = await self.createContract(contract)
            contracts.append(contract)
            
        return contracts[0] if len(contracts) == 1 else contracts

    # -----------------------------------------
    async def createContinuousFuturesContract(self, symbol, exchange = "GLOBEX",
                                          output = "contract", is_retry = False):
        """
        Create a continuous futures contract.
        
        Args:
            symbol: Futures symbol
            exchange: Exchange code
            output: Output type ('contract' or 'tuple')
            is_retry: Whether this is a retry attempt
            
        Returns:
            Futures contract object or tuple
        """
        # Create a continuous futures contract
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "CONTFUT"
        contract.exchange = exchange
        contfut_contract = await self.createContract(contract)
        
        # Wait for contract details
        for _ in range(25):
            # await asyncio.sleep(0.01)
            contfut = self.contract_details(contfut_contract)
            if contfut.get("tickerId", 0) != 0 and contfut.get("conId", 0) != 0:
                break
                
        # Can't find contract? Retry once
        if contfut.get("conId", 0) == 0:
            if not is_retry:
                return await self.createContinuousFuturesContract(symbol, exchange, output, True,)
            raise ValueError(f"Can't find a valid Contract using this combination ({symbol}/{exchange})")
            
        # Get contract details
        ticker_id = contfut.get("tickerId")
        expiry = contfut.get("contractMonth", "")
        currency = contfut.get("summary", {}).get("currency", "USD")
        multiplier = contfut.get("summary", {}).get("multiplier", "")
        
        # Delete continuous placeholder
        if ticker_id in self.contracts:
            del self.contracts[ticker_id]
        if ticker_id in self._contract_details:
            del self._contract_details[ticker_id]
            
        # Return tuple or contract
        if output == "tuple":
            return (symbol, "FUT", exchange, currency, expiry, 0.0, "", multiplier)
            
        return await self.createFuturesContract(symbol, currency, expiry, exchange, multiplier)


    # -----------------------------------------
    async def createOptionContract(self, symbol, expiry = None, strike = 0.0, otype = "C",
                                  currency = "USD", sec_type = "OPT", exchange = "SMART", multiplier=""):
        """
        Create an option contract.
        
        Args:
            symbol: Underlying symbol
            expiry: Expiry date(s) in YYYYMMDD format
            strike: Strike price(s)
            otype: Option type(s) ('C' for Call or 'P' for Put)
            currency: Currency code
            sec_type: Security type ('OPT' or 'FOP')
            exchange: Exchange code
            
        Returns:
            Option contract object or list of contracts
        """
        # Handle multiple parameters
        expiries = [expiry] if expiry and not isinstance(expiry, list) else expiry
        strikes = [strike] if not isinstance(strike, list) else strike
        otypes = [otype] if not isinstance(otype, list) else otype
        
        contracts = []
        for opt_expiry in expiries or [""]:
            for opt_strike in strikes or [0.0]:
                for opt_otype in otypes or ["C"]:
                    contract = Option(symbol=symbol, lastTradeDateOrContractMonth=opt_expiry,
                                     strike=opt_strike, right=opt_otype, exchange=exchange,
                                     multiplier=multiplier, currency=currency)
                    # Override secType if needed (for FOP)
                    if sec_type != "OPT":
                        contract.secType = sec_type
                    contract = await self.createContract(contract)
                    contracts.append(contract)
                    
        return contracts[0] if len(contracts) == 1 else contracts
        
    async def createForexContract(self, symbol, currency = "USD", exchange = "IDEALPRO"):
        """
        Create a forex contract.
        
        Args:
            symbol: Currency symbol (e.g., 'EUR' for EUR/USD)
            currency: Quote currency
            exchange: Exchange code
            
        Returns:
            Forex contract object
        """
        contract = Forex(pair=f'{symbol}{currency}', symbol=symbol, currency=currency, exchange=exchange)
        return await self.createContract(contract)
        
    async def createIndexContract(self, symbol, currency = "USD", exchange = "CBOE"):
        """
        Create an index contract.
        
        Args:
            symbol: Index symbol
            currency: Currency code
            exchange: Exchange code
            
        Returns:
            Index contract object
        """
        contract = Index(symbol=symbol, exchange=exchange, currency=currency)
        return await self.createContract(contract)
        
    async def createComboLeg(self, contract, action, ratio = 1, exchange = None):
        """
        Create a combo leg for a combo contract.
        
        Args:
            contract: Contract for the leg
            action: Action ('BUY' or 'SELL')
            ratio: Leg ratio
            exchange: Exchange code (defaults to contract's exchange)
            
        Returns:
            ComboLeg object
        """
        leg = ComboLeg()
        
        # Get contract ID
        loops = 0
        con_id = 0
        while con_id == 0 and loops < 100:
            con_id = self.getConId(contract)
            loops += 1
            await asyncio.sleep(0.05)
            
        leg.conId = con_id
        leg.ratio = abs(ratio)
        leg.action = action
        leg.exchange = contract.exchange if exchange is None else exchange
        leg.openClose = 0
        leg.shortSaleSlot = 0
        leg.designatedLocation = ""
        
        return leg
        
    async def createComboContract(self, symbol, legs, currency = "USD", exchange = None):
        """
        Create a combo contract with multiple legs.
        
        Args:
            symbol: Symbol for the combo
            legs: List of ComboLeg objects
            currency: Currency code
            exchange: Exchange code (defaults to first leg's exchange)
            
        Returns:
            Combo contract object
        """
        exchange = legs[0].exchange if exchange is None else exchange
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "BAG"
        contract.exchange = exchange
        contract.currency = currency
        contract.comboLegs = legs
        return await self.createContract(contract)

    # ---------------------------------------
    def createOrder(self, quantity, price=0., stop=0., tif="DAY",
                fillorkill=False, iceberg=False, transmit=True, rth=False,
                account=None, **kwargs):
        """
        Create a trading order
        
        Parameters:
            quantity: Order quantity, positive for buy, negative for sell
            price: Limit price, 0 for market order
            stop: Stop price
            tif: Time-in-force, such as DAY, GTC, IOC, GTD, OPG, ...
            fillorkill: Whether to use fill-or-kill
            iceberg: Whether to use iceberg order
            transmit: Whether to transmit the order immediately
            rth: Whether order is valid only during regular trading hours
            account: Trading account
            **kwargs: Additional parameters
        
        Returns:
            Order object
        """
        
        # Create order object
        order = Order()
        
        # Set order direction and quantity
        order.action = "BUY" if quantity > 0 else "SELL"
        order.totalQuantity = abs(int(quantity))
        
        # Set order type
        if "orderType" in kwargs:
            order.orderType = kwargs["orderType"]
            if kwargs["orderType"] == "MOO":
                order.orderType = "MKT"
                tif = "OPG"
            elif kwargs["orderType"] == "LOO":
                order.orderType = "LMT"
                tif = "OPG"
        else:
            order.orderType = "MKT" if price == 0 else "LMT"
        
        # Set prices
        order.lmtPrice = price  # Limit price
        order.auxPrice = kwargs["auxPrice"] if "auxPrice" in kwargs else stop  # Stop price
        
        # Set time-in-force and execution conditions
        order.tif = tif.upper()  
        order.allOrNone = bool(fillorkill)
        order.hidden = bool(iceberg)
        order.transmit = bool(transmit)
        order.outsideRth = bool(rth == False and tif.upper() != "OPG")
        
        # Set account
        account_code = self._get_active_account(account)
        if account_code is not None:
            order.account = account_code
        
        # Iceberg order display quantity
        if iceberg and ("blockOrder" in kwargs):
            order.blockOrder = kwargs["blockOrder"]
        
        # Relative order percentage offset
        if "percentOffset" in kwargs:
            order.percentOffset = kwargs["percentOffset"]
        
        # Parent order ID, used for bracket orders and trailing stops
        if "parentId" in kwargs:
            order.parentId = kwargs["parentId"]
        
        # OCA group (Order Cancels All), used for bracket orders and trailing stops
        if "ocaGroup" in kwargs:
            order.ocaGroup = kwargs["ocaGroup"]
            if "ocaType" in kwargs:
                order.ocaType = kwargs["ocaType"]
            else:
                order.ocaType = 2  # Proportionally reduce remaining orders' size
        
        # Trailing stop order
        if "trailingPercent" in kwargs:
            order.trailingPercent = kwargs["trailingPercent"]
        
        # Trailing limit stop order
        if "trailStopPrice" in kwargs:
            order.trailStopPrice = kwargs["trailStopPrice"]
        
        return order
    
    # ---------------------------------------
    def placeOrder(self, contract, order, orderId=None, account=None):
        """ 
        Place order on IB TWS
        
        Parameters:
            contract: Contract object
            order: Order object
            orderId: Order ID, uses current orderId if None
            account: Account code
            
        Returns:
            Order ID
        """
        try:
            # Handle None contract
            if contract is None:
                self._logger.error("Cannot place order with None contract")
                return None
                
            # Ensure prices conform to contract's minimum tick size
            ticksize = self.contractDetails(contract)["minTick"]
            order.lmtPrice = self.roundClosestValid(order.lmtPrice, ticksize)
            order.auxPrice = self.roundClosestValid(order.auxPrice, ticksize)
            
            # Set account
            account_code = self._get_active_account(account)
            if account_code is not None:
                order.account = account_code
            
            # Use ib_async's placeOrder method
            trade = self.ib.placeOrder(contract, order)
            # trade.statusEvent += self._on_order_status

            # self.ib.sleep(0.1)
            
            # Record order information
            self.orders[order.orderId] = {
                "id":           order.orderId,
                "symbol":       self.contractString(contract),
                "contract":     contract,
                "status":       "SENT",
                "reason":       None,
                "avgFillPrice": 0.,
                "parentId":     0,
                # "time":         datetime.fromtimestamp(int(self.time)),
                "account":      None
            }
            
            # Record account information
            if hasattr(order, "account"):
                self.orders[order.orderId]["account"] = order.account
            
            # Return order ID
            return trade
            
        except Exception as e:
            self._logger.error(f"Error placing order: {e}")
            return None

    # ---------------------------------------
    async def requestContractDetails(self, contract):
        """
        Request contract details from IB API.

        """
        tickerId = self.tickerId(contract)
        try:
            details = await self.ib.reqContractDetailsAsync(contract)
            
            if not details:
                self._logger.warning(f"No contract details returned for {contract}")
                return
                
            self._contract_details.append(*details)
            # Process contract details
            # await self._handle_contract_details(tickerId, details)
            
        except Exception as e:
            self._logger.error(f"Error requesting contract details: {e}")

    # -----------------------------------------
    async def _handle_contract_details(self, tickerId, details):
        """
        Process contract details received from IB API.
        
        Args:
            tickerId: Ticker ID for the contract
            details: List of ContractDetails objects
        """
        if not details:
            return
            
        # Create a dictionary to store contract details
        details_dict = {
            'tickerId': tickerId,
            'downloaded': True,
            'contracts': [detail.contract for detail in details],
            'conId': details[0].contract.conId,
            'contractMonth': details[0].contractMonth,
            'industry': details[0].industry,
            'category': details[0].category,
            'subcategory': details[0].subcategory,
            'timeZoneId': details[0].timeZoneId,
            'tradingHours': details[0].tradingHours,
            'liquidHours': details[0].liquidHours,
            'evRule': details[0].evRule,
            'evMultiplier': details[0].evMultiplier,
            'minTick': details[0].minTick,
            'orderTypes': details[0].orderTypes,
            'validExchanges': details[0].validExchanges,
            'priceMagnifier': details[0].priceMagnifier,
            'underConId': details[0].underConId,
            'longName': details[0].longName,
            'marketName': details[0].marketName,
        }
        
        # Add summary information
        if len(details) > 1:
            details_dict['contractMonth'] = ""
            # Use closest expiration as summary
            expirations = await self.getExpirations(self.contracts[tickerId])
            if expirations:
                contract = details_dict['contracts'][-len(expirations)]
                details_dict['summary'] = vars(contract)
            else:
                details_dict['summary'] = vars(details_dict['contracts'][0])
        else:
            details_dict['summary'] = vars(details_dict['contracts'][0])
            
        # Store contract details
        self._contract_details[tickerId] = details_dict
        
        # Add local symbol mapping
        for detail in details:
            contract = detail.contract
            if contract.localSymbol and contract.localSymbol not in self.localSymbolExpiry:
                self.localSymbolExpiry[contract.localSymbol] = detail.contractMonth
                
        # Add contracts to the contracts dictionary
        for contract in details_dict['contracts']:
            contract_string = self.contractString(contract)
            contract_ticker_id = self.tickerId(contract_string)
            self.contracts[contract_ticker_id] = contract
            
            # If this is a different ticker ID than the original, create a separate entry
            if contract_ticker_id != tickerId:
                contract_details = details_dict.copy()
                contract_details['summary'] = vars(contract)
                contract_details['contracts'] = [contract]
                self._contract_details[contract_ticker_id] = contract_details

    # -----------------------------------------
    def getConId(self, contract):
        """
        Get the contract ID for a contract, symbol, or ticker ID.
        
        Args:
            contract_identifier: Contract object, symbol string, or ticker ID
            
        Returns:
            Contract ID
        """
        for c in self.contracts:
            if contract.conId == c.conId:
                return c.conId
        
        return 0

        # details = self.contractDetails(contract_identifier)
        # return details.get("conId", 0)
    
    # -----------------------------------------
    def getContract(self, contract):
        """
        Get the contract ID for a contract, symbol, or ticker ID.
        
        Args:
            contract_identifier: Contract object, symbol string, or ticker ID
            
        Returns:
            Contract ID
        """
        for c in self.contracts:
            if contract.conId == c.conId:
                return c
        
        return None

    # -----------------------------------------
    def isMultiContract(self, contract):
        """
        Check if a contract has multiple sub-contracts with different expiries/strikes/sides.
        
        """
        # Futures with no expiry
        if contract.secType == "FUT" and not contract.lastTradeDateOrContractMonth:
            return True
            
        # Options with missing fields
        if contract.secType in ("OPT", "FOP") and (
            not contract.lastTradeDateOrContractMonth or 
            not contract.strike or 
            not contract.right
        ):
            return True
            
        # Check if we have multiple contracts in the details
        tickerId = self.tickerId(contract)
        if tickerId in self._contract_details and len(self._contract_details[tickerId]["contracts"]) > 1:
            return True
            
        return False

    # -----------------------------------------
    async def getExpirations(self, contract_identifier, expired = 0):
        """
        Get available expirations for a contract.
        
        Args:
            contract_identifier: Contract object, symbol string, or ticker ID
            expired: Number of expired contracts to include (0 = none)
            
        Returns:
            Tuple of expiration dates as integers (YYYYMMDD)
        """
        details = self.contractDetails(contract_identifier)
        contracts = details.get("contracts", [])
     
        if not contracts or contracts[0].secType not in ("FUT", "FOP", "OPT"):
            return tuple()
            
        # Collect expirations
        expirations = []
        for contract in contracts:
            if contract.lastTradeDateOrContractMonth:
                expirations.append(int(contract.lastTradeDateOrContractMonth))
                
        # Remove expired contracts
        today = int(datetime.now().strftime("%Y%m%d"))
        if expirations:
            closest = min(expirations, key=lambda x: abs(x - today))
            idx = expirations.index(closest) - expired
            if idx >= 0:
                expirations = expirations[idx:]
            
        return tuple(sorted(expirations))

    # -----------------------------------------
    async def getStrikes(self, contract_identifier, smin = None, smax = None):
        """
        Get available strikes for an option contract.
        
        Args:
            contract_identifier: Contract object, symbol string, or ticker ID
            smin: Minimum strike price
            smax: Maximum strike price
            
        Returns:
            Tuple of strike prices
        """
        details = self.contractDetails(contract_identifier)
        contracts = details.get("contracts", [])
        
        if not contracts or contracts[0].secType not in ("FOP", "OPT"):
            return tuple()
            
        # Collect strikes
        strikes = []
        for contract in contracts:
            strikes.append(contract.strike)
            
        # Filter by min/max
        if smin is not None or smax is not None:
            smin = smin if smin is not None else 0
            smax = smax if smax is not None else float('inf')
            strikes = [s for s in strikes if smin <= s <= smax]
            
        return tuple(sorted(strikes))
    
    # -----------------------------------------
    async def registerContract(self, contract):
        """
        Register a contract that was received from a callback.
        
        Args:
            contract: Contract object to register
        """
        try:
            if self.getConId(contract) == 0:
                # contract_tuple = self.contract_to_tuple(contract)
                # add timeout
                await asyncio.wait_for(
                    self.createContract(contract),
                    timeout=10.0
                )
        except asyncio.TimeoutError:
            self._logger.error(f"Contract registration timed out: {contract}")
        except Exception as e:
            self._logger.error(f"Error registering contract: {str(e)}")
    
    # -----------------------------------------
    # Position handling
    # -----------------------------------------
    def _onPositionUpdateHandler(self, position):
        """
        Handle position updates from IB.
        
        Args:
            position: Position object from IB
        """
        try:
            # contract identifier
            contract_tuple = self.contract_to_tuple(position.contract)
            contractString = self.contractString(contract_tuple)
            
            # try creating the contract (only if event loop is running)
            try:
                asyncio.create_task(self.registerContract(position.contract))
            except RuntimeError:
                # No event loop running, skip async registration
                pass
            # self._logger.debug(f"Position of contract: {position.contract} updated.")
            
            # Get symbol
            symbol = position.contract.symbol
            
            # Create account entry if it doesn't exist
            if position.account not in self._positions:
                self._positions[position.account] = {}
                
            # Create or update position
            self._positions[position.account][contractString] = {
                "symbol": contractString,
                "position": position.position,
                "avgCost": position.avgCost,
                "account": position.account
            }
                
            # If position is zero, remove the position entry
            # if position.position == 0:
            #     if contractString in self._positions[position.account]:
            #         del self._positions[position.account][contractString]
            #         self._logger.debug(f"Removed position for {position.account}: {symbol} (position closed)")
            # else:
            # Update position
            # self._positions[position.account][contractString] = position
            self._logger.debug(
                f"Updated position for {position.account}: {symbol} = {position.position} @ {position.avgCost}")
            
        except Exception as e:
            self._logger.error(f"Error handling position update: {e}")

        # TODO:fire callback
        # self.ibCallback(caller="handlePosition", msg=position)

    # @property
    # def positions(self):
    #     return self.getPositions()
    
    @property
    def positions(self):
        return self._positions
    
    @property
    def position(self):
        return self.getPosition()

    def getPosition(self, account=None):
        if len(self._positions) == 0:
            return {}

        account = self._get_active_account(account)

        if account is None:
            if len(self._positions) > 1:
                raise ValueError("Must specify account number as multiple accounts exists.")
            account_data = self._positions[list(self._positions.keys())[0]]
            # Validate that the data is properly formatted
            if not isinstance(account_data, dict):
                raise ValueError("Position data is corrupted - expected dict but got %s" % type(account_data))
            return account_data

        if account in self._positions:
            account_data = self._positions[account]
            # Validate that the data is properly formatted
            if not isinstance(account_data, dict):
                raise ValueError("Position data is corrupted - expected dict but got %s" % type(account_data))
            return account_data

        raise ValueError("Account %s not found in account list" % account)

    # -----------------------------------------
    # Portfolio handling
    # -----------------------------------------
    def _onPortfolioUpdateHandler(self, portfolio):
        """
        Handle portfolio updates from IB.
        
        Args:
            portfolio: PortfolioItem objects from IB
        """
        try:
            # contract identifier
            contract_tuple = self.contract_to_tuple(portfolio.contract)
            contractString = self.contractString(contract_tuple)
            
            # try creating the contract
            # asyncio.create_task(self.registerContract(portfolio.contract))
            
            # Get symbol
            symbol = portfolio.contract.symbol
            
            # Create account entry if it doesn't exist
            if portfolio.account not in self._portfolios:
                self._portfolios[portfolio.account] = {}
                # self._portfolios_items[portfolio.account] = []
                
            # Calculate total P&L
            total_pnl = portfolio.unrealizedPNL + portfolio.realizedPNL
            
            # Create or update portfolio item
            # self._portfolios[portfolio.account][contractString] = portfolio
            self._portfolios[portfolio.account][contractString] = {
                "symbol": contractString,
                "position": portfolio.position,
                "marketPrice": portfolio.marketPrice,
                "marketValue": portfolio.marketValue,
                "averageCost": portfolio.averageCost,
                "unrealizedPNL": portfolio.unrealizedPNL,
                "realizedPNL": portfolio.realizedPNL,
                "totalPNL": total_pnl,
                "account": portfolio.account
            }
            # self._portfolios_items[portfolio.account].append(portfolio)
            
            self._logger.debug(
                f"Updated portfolio for {portfolio.account}: {symbol} = {portfolio.position} @ {portfolio.marketPrice}")

            # TODO:fire callback
            # self.ibCallback(caller="handlePortfolio", msg=portfolio)
            
        except Exception as e:
            self._logger.error(f"Error handling portfolio update: {e}")

    @property
    def portfolios(self):
        return self._portfolios
    

    @property
    def portfolio(self):
        return self.getPortfolio()
        # return [ p for p in self.portfolios if p.account == self._default_account]

    def getPortfolio(self, account=None):
        if len(self._portfolios) == 0:
            return {}

        account = self._get_active_account(account)

        if account is None:
            return []
            # if len(self._portfolios) > 1:
            #     raise ValueError("Must specify account number as multiple accounts exists.")
            # return self._portfolios[list(self._portfolios.keys())[0]]

        if account in self._portfolios:
            return self._portfolios[account]

        raise ValueError("Account %s not found in account list" % account)

    # -----------------------------------------
    # Order Creation Methods
    # -----------------------------------------
    def createTargetOrder(self, quantity, parentId=0,
            target=0., orderType=None, transmit=True, group=None, tif="DAY",
            rth=False, account=None):
        """ 
        Creates TARGET order 
        
        Args:
            quantity: Order quantity
            parentId: Parent order ID
            target: Target price
            orderType: Order type
            transmit: Whether to transmit the order
            group: OCA group name
            tif: Time-in-force
            rth: Whether order is valid only during regular trading hours
            account: Trading account
            
        Returns:
            Order object
        """
        params = {
            "quantity": quantity,
            "price": target,
            "transmit": transmit,
            "orderType": orderType,
            "ocaGroup": group,
            "parentId": parentId,
            "rth": rth,
            "tif": tif,
            "account": self._get_active_account(account)
        }
        
        # default order type is "Market if Touched"
        if orderType is None:
            params['orderType'] = "MIT"
            params['auxPrice'] = target
            del params['price']

        order = self.createOrder(**params)
        return order

    # -----------------------------------------
    def createStopOrder(self, quantity, parentId=0, stop=0., trail=None,
            transmit=True, trigger=None, group=None, stop_limit=False,
            rth=False, tif="DAY", account=None, **kwargs):
        """ 
        Creates STOP order 
        
        Args:
            quantity: Order quantity
            parentId: Parent order ID
            stop: Stop price
            trail: Trail type ('percent' or amount)
            transmit: Whether to transmit the order
            trigger: Trigger price
            group: OCA group name
            stop_limit: Whether to use a stop-limit order
            rth: Whether order is valid only during regular trading hours
            tif: Time-in-force
            account: Trading account
            **kwargs: Additional parameters
            
        Returns:
            Order object
        """
        stop_limit_price = 0
        if stop_limit is not False:
            if stop_limit is True:
                stop_limit_price = stop
            else:
                try:
                    stop_limit_price = float(stop_limit)
                except Exception:
                    stop_limit_price = stop

        trailStopPrice = trigger if trigger else stop_limit_price
        if quantity > 0:
            trailStopPrice -= abs(stop)
        elif quantity < 0:
            trailStopPrice -= abs(stop)

        order_data = {
            "quantity": quantity,
            "trailStopPrice": trailStopPrice,
            "stop": abs(stop),
            "price": stop_limit_price,
            "transmit": transmit,
            "ocaGroup": group,
            "parentId": parentId,
            "rth": rth,
            "tif": tif,
            "account": self._get_active_account(account)
        }

        if trail:
            order_data['orderType'] = "TRAIL"
            if "orderType" in kwargs:
                order_data['orderType'] = kwargs["orderType"]
            elif stop_limit:
                order_data['orderType'] = "TRAIL LIMIT"

            if trail == "percent":
                order_data['trailingPercent'] = stop
            else:
                order_data['auxPrice'] = stop
        else:
            order_data['orderType'] = "STP"
            if stop_limit:
                order_data['orderType'] = "STP LMT"

        order = self.createOrder(**order_data)
        return order
    
    # -----------------------------------------
    def createTriggerableTrailingStop(self, symbol, quantity=1,
            triggerPrice=0, trailPercent=100., trailAmount=0.,
            parentId=0, stopOrderId=None, targetOrderId=None,
            account=None, **kwargs):
        """
        Adds order to triggerable list
        
        IMPORTANT! For trailing stop to work you'll need
            1. real time market data subscription for the tracked ticker
            2. the python/algo script to be kept alive
            
        Args:
            symbol: Contract symbol
            quantity: Order quantity
            triggerPrice: Price at which to trigger the trailing stop
            trailPercent: Trailing percentage
            trailAmount: Trailing amount
            parentId: Parent order ID
            stopOrderId: Stop order ID
            targetOrderId: Target order ID
            account: Trading account
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with trailing stop parameters
        """
        # Initialize the triggerableTrailingStops dictionary if it doesn't exist
        if not hasattr(self, 'triggerableTrailingStops'):
            self.triggerableTrailingStops = {}

        ticksize = self.contractDetails(symbol)["minTick"]

        self.triggerableTrailingStops[symbol] = {
            "parentId": parentId,
            "stopOrderId": stopOrderId,
            "targetOrderId": targetOrderId,
            "triggerPrice": triggerPrice,
            "trailAmount": abs(trailAmount),
            "trailPercent": abs(trailPercent),
            "quantity": quantity,
            "ticksize": ticksize,
            "account": self._get_active_account(account)
        }

        return self.triggerableTrailingStops[symbol]

    # -----------------------------------------
    def createBracketOrder(self, contract, quantity,
                entry=0., target=0., stop=0.,
                targetType=None, stopType=None,
                trailingStop=False,  # (pct/amt/False)
                trailingValue=None,  # value to train by (amt/pct)
                trailingTrigger=None,  # (price where hard stop starts trailing)
                group=None, tif="DAY",
                fillorkill=False, iceberg=False, rth=False,
                transmit=True, account=None, **kwargs):
            """
            Creates One Cancels All Bracket Order
            
            Args:
                contract: Contract object
                quantity: Order quantity
                entry: Entry price (0 for market order)
                target: Target/profit price (0 to disable)
                stop: Stop/loss price (0 to disable)
                targetType: Target order type
                stopType: Stop order type
                trailingStop: Trailing stop type ('pct', 'amt', or False)
                trailingValue: Value to trail by (amount or percentage)
                trailingTrigger: Price where hard stop starts trailing
                group: OCA group name
                tif: Time-in-force
                fillorkill: Whether to use fill-or-kill
                iceberg: Whether to use iceberg order
                rth: Whether order is valid only during regular trading hours
                transmit: Whether to transmit the order
                account: Trading account
                **kwargs: Additional parameters
                
            Returns:
                Dictionary with order IDs
            """
            import time
            
            if group is None:
                group = "bracket_" + str(int(time.time()))

            account = self._get_active_account(account)

            # main order
            entryOrder = self.createOrder(quantity, price=entry, transmit=False,
                            tif=tif, fillorkill=fillorkill, iceberg=iceberg,
                            rth=rth, account=account, **kwargs)

            trade = self.placeOrder(contract, entryOrder)
            if trade is None:
                self._logger.error("Failed to place entry order for bracket order")
                return None
            entryOrderId = trade.order.orderId

            # target
            targetOrderId = 0
            if target > 0 or targetType == "MOC":
                targetOrder = self.createTargetOrder(-quantity,
                                parentId=entryOrderId,
                                target=target,
                                transmit=False if stop > 0 else True,
                                orderType=targetType,
                                group=group,
                                rth=rth,
                                tif=tif,
                                account=account
                            )

                targetTrade = self.placeOrder(contract, targetOrder)
                if targetTrade is None:
                    self._logger.error("Failed to place target order for bracket order")
                    targetOrderId = 0
                else:
                    targetOrderId = targetTrade.order.orderId

            # stop
            stopOrderId = 0
            if stop > 0:
                stop_limit = stopType and stopType.upper() in ["LIMIT", "LMT"]
                
                stopOrder = self.createStopOrder(-quantity,
                                parentId=entryOrderId,
                                stop=stop,
                                trail=None,
                                transmit=transmit,
                                group=group,
                                rth=rth,
                                tif=tif,
                                stop_limit=stop_limit,
                                account=account
                            )

                stopTrade = self.placeOrder(contract, stopOrder)
                if stopTrade is None:
                    self._logger.error("Failed to place stop order for bracket order")
                    stopOrderId = 0
                else:
                    stopOrderId = stopTrade.order.orderId

                # triggered trailing stop?
                if trailingStop and trailingTrigger and trailingValue:
                    trailing_params = {
                        "symbol": self.contractString(contract),
                        "quantity": -quantity,
                        "triggerPrice": trailingTrigger,
                        "parentId": entryOrderId,
                        "stopOrderId": stopOrderId,
                        "targetOrderId": targetOrderId if targetOrderId != 0 else None,
                        "account": account
                    }
                    if trailingStop.lower() in ['amt', 'amount']:
                        trailing_params["trailAmount"] = trailingValue
                    elif trailingStop.lower() in ['pct', 'percent']:
                        trailing_params["trailPercent"] = trailingValue

                    self.createTriggerableTrailingStop(**trailing_params)

            return {
                "group": group,
                "entryOrderId": entryOrderId,
                "targetOrderId": targetOrderId,
                "stopOrderId": stopOrderId
            }