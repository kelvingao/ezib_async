"""
Asynchronous Contract Management for Interactive Brokers API.

This module provides a ContractManager class that handles the creation,
tracking, and management of various contract types using ib_async.
"""
import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime

from ib_async import (
    Contract, 
    Stock, 
    Option, 
    Future, 
    Forex, 
    Index, 
    CFD,
    Commodity,
    Bond,
    ContractDetails,
    ComboLeg
)

logger = logging.getLogger(__name__)


class ContractManager:
    """
    Manages contract creation, tracking, and details for Interactive Brokers API.
    
    This class provides functionality for:
    - Creating various contract types (stocks, options, futures, etc.)
    - Tracking contracts by ticker ID
    - Retrieving contract details
    - Converting between contract objects and string representations
    
    Attributes:
        _conn: Connection manager for IB API
        _contracts: Dictionary of contracts indexed by ticker ID
        _ticker_ids: Dictionary mapping symbols to ticker IDs
        _contract_details: Dictionary of contract details indexed by ticker ID
        _local_symbol_expiry: Dictionary mapping local symbols to expiry dates
    """
    
    def __init__(self, connection_manager):
        """
        Initialize the ContractManager.
        
        Args:
            connection_manager: ConnectionManager instance for IB API
        """
        self._conn = connection_manager
        self._contracts: Dict[int, Contract] = {}
        self._ticker_ids: Dict[int, str] = {0: "SYMBOL"}
        self._contract_details: Dict[int, Dict[str, Any]] = {}
        self._temp_contract_details: Dict[int, Dict[str, Any]] = {}
        self._local_symbol_expiry: Dict[str, str] = {}
        
    @property
    def ib(self):
        """Get the IB client instance from the connection manager."""
        return self._conn.client
    
    @staticmethod
    def round_closest_valid(val: float, res: float = 0.01, decimals: Optional[int] = None) -> float:
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
            
        if decimals is None and "." in str(res):
            decimals = len(str(res).split('.')[1])
            
        return round(round(val / res) * res, decimals)
        
    def ticker_id(self, contract_identifier: Union[Contract, str]) -> int:
        """
        Get the ticker ID for a contract or symbol.
        
        If the contract or symbol doesn't have a ticker ID yet, a new one is assigned.
        
        Args:
            contract_identifier: Contract object or symbol string
            
        Returns:
            Ticker ID for the contract or symbol
        """
        # Handle contract object
        symbol = contract_identifier
        if isinstance(symbol, Contract):
            symbol = self.contract_to_string(symbol)
            
        # Check if symbol already has a ticker ID
        for ticker_id, ticker_symbol in self._ticker_ids.items():
            if symbol == ticker_symbol:
                return ticker_id
                
        # Assign new ticker ID
        ticker_id = len(self._ticker_ids)
        self._ticker_ids[ticker_id] = symbol
        return ticker_id
        
    def ticker_symbol(self, ticker_id: int) -> str:
        """
        Get the symbol for a ticker ID.
        
        Args:
            ticker_id: Ticker ID to look up
            
        Returns:
            Symbol string for the ticker ID
        """
        try:
            return self._ticker_ids[ticker_id]
        except KeyError:
            return ""
            
    @staticmethod
    def contract_to_tuple(contract: Contract) -> Tuple:
        """
        Convert a contract object to a tuple representation.
        
        Args:
            contract: Contract object
            
        Returns:
            Tuple representation of the contract
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
        
    def contract_to_string(self, contract: Union[Contract, Tuple], separator: str = "_") -> str:
        """
        Convert a contract object or tuple to a string representation.
        
        Args:
            contract: Contract object or tuple
            separator: Separator to use between contract elements
            
        Returns:
            String representation of the contract
        """
        local_symbol = ""
        contract_tuple = contract
        
        if not isinstance(contract, tuple):
            local_symbol = contract.localSymbol
            contract_tuple = self.contract_to_tuple(contract)
            
        try:
            if contract_tuple[1] in ("OPT", "FOP"):
                # Format strike price for options
                strike = '{:0>5d}'.format(int(contract_tuple[5])) + \
                    format(contract_tuple[5], '.3f').split('.')[1]
                    
                contract_string = (contract_tuple[0] + str(contract_tuple[4]) +
                                  contract_tuple[6][0] + strike, contract_tuple[1])
                                  
            elif contract_tuple[1] == "FUT":
                # Format expiry for futures
                exp = str(contract_tuple[4])[:6]
                month_codes = {
                    1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
                    7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z'
                }
                exp = month_codes[int(exp[4:6])] + exp[:4]
                contract_string = (contract_tuple[0] + exp, contract_tuple[1])
                
            elif contract_tuple[1] == "CASH":
                contract_string = (contract_tuple[0] + contract_tuple[3], contract_tuple[1])
                
            else:  # STK
                contract_string = (contract_tuple[0], contract_tuple[1])
                
            # Construct string
            contract_string = separator.join(
                str(v) for v in contract_string).replace(separator + "STK", "")
                
        except Exception as e:
            logger.error(f"Error converting contract to string: {e}")
            contract_string = contract_tuple[0]
            
        return contract_string.replace(" ", "_").upper()
        
    async def register_contract(self, contract: Contract) -> None:
        """
        Register a contract that was received from a callback.
        
        Args:
            contract: Contract object to register
        """
        if contract.exchange == "":
            return
            
        if self.get_con_id(contract) == 0:
            contract_tuple = self.contract_to_tuple(contract)
            await self.create_contract(contract_tuple)
            
    def get_con_id(self, contract_identifier: Union[Contract, str, int]) -> int:
        """
        Get the contract ID for a contract, symbol, or ticker ID.
        
        Args:
            contract_identifier: Contract object, symbol string, or ticker ID
            
        Returns:
            Contract ID
        """
        if isinstance(contract_identifier, Contract):
            ticker_id = self.ticker_id(contract_identifier)
        else:
            if isinstance(contract_identifier, int) or (
                isinstance(contract_identifier, str) and contract_identifier.isdigit()
            ):
                ticker_id = int(contract_identifier)
            else:
                ticker_id = self.ticker_id(contract_identifier)
                
        details = self.contract_details(ticker_id)
        return details.get("conId", 0)
        
    def contract_details(self, contract_identifier: Union[Contract, str, int]) -> Dict[str, Any]:
        """
        Get contract details for a contract, symbol, or ticker ID.
        
        Args:
            contract_identifier: Contract object, symbol string, or ticker ID
            
        Returns:
            Dictionary of contract details
        """
        if isinstance(contract_identifier, Contract):
            ticker_id = self.ticker_id(contract_identifier)
        else:
            if isinstance(contract_identifier, int) or (
                isinstance(contract_identifier, str) and contract_identifier.isdigit()
            ):
                ticker_id = int(contract_identifier)
            else:
                ticker_id = self.ticker_id(contract_identifier)
                
        # Check if we have the contract details
        if ticker_id in self._contract_details:
            return self._contract_details[ticker_id]
        elif ticker_id in self._temp_contract_details:
            return self._temp_contract_details[ticker_id]
            
        # Default values if no details are available
        return {
            'tickerId': 0,
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
        
    async def create_contract(self, contract_tuple: Tuple, **kwargs) -> Contract:
        """
        Create a contract from a tuple representation.
        
        Args:
            contract_tuple: Tuple representation of the contract
            **kwargs: Additional contract parameters
            
        Returns:
            Created contract object
        """
        contract_string = self.contract_to_string(contract_tuple)
        ticker_id = self.ticker_id(contract_string)
        
        # Create a new Contract object
        new_contract = Contract()
        new_contract.symbol = contract_tuple[0]
        new_contract.secType = contract_tuple[1]
        new_contract.exchange = contract_tuple[2] or "SMART"
        new_contract.currency = contract_tuple[3] or "USD"
        new_contract.lastTradeDateOrContractMonth = contract_tuple[4] or ""
        new_contract.strike = contract_tuple[5] or 0.0
        new_contract.right = contract_tuple[6] or ""
        
        if len(contract_tuple) >= 8:
            new_contract.multiplier = contract_tuple[7]
            
        # Include expired contracts for historical data
        new_contract.includeExpired = new_contract.secType in ["FUT", "OPT", "FOP"]
        
        # Add combo legs if provided
        if "combo_legs" in kwargs:
            new_contract.comboLegs = kwargs["combo_legs"]
            
        # Add contract to pool
        self._contracts[ticker_id] = new_contract
        
        # Request contract details if not a combo contract
        if "combo_legs" not in kwargs:
            try:
                await self.request_contract_details(new_contract)
                if self.is_multi_contract(new_contract):
                    await asyncio.sleep(1.5)
                else:
                    await asyncio.sleep(0.5)
            except KeyboardInterrupt:
                logger.warning("Contract details request interrupted")
                
        return new_contract
        
    async def request_contract_details(self, contract: Contract) -> None:
        """
        Request contract details from IB API.
        
        Args:
            contract: Contract to request details for
        """
        ticker_id = self.ticker_id(contract)
        try:
            details = await self.ib.reqContractDetailsAsync(contract)
            
            if not details:
                logger.warning(f"No contract details returned for {contract.symbol}")
                return
                
            # Process contract details
            await self._process_contract_details(ticker_id, details)
            
        except Exception as e:
            logger.error(f"Error requesting contract details: {e}")
            
    async def _process_contract_details(self, ticker_id: int, details_list: List[ContractDetails]) -> None:
        """
        Process contract details received from IB API.
        
        Args:
            ticker_id: Ticker ID for the contract
            details_list: List of ContractDetails objects
        """
        if not details_list:
            return
            
        # Create a dictionary to store contract details
        details_dict = {
            'tickerId': ticker_id,
            'downloaded': True,
            'contracts': [detail.contract for detail in details_list],
            'conId': details_list[0].contract.conId,
            'contractMonth': details_list[0].contractMonth,
            'industry': details_list[0].industry,
            'category': details_list[0].category,
            'subcategory': details_list[0].subcategory,
            'timeZoneId': details_list[0].timeZoneId,
            'tradingHours': details_list[0].tradingHours,
            'liquidHours': details_list[0].liquidHours,
            'evRule': details_list[0].evRule,
            'evMultiplier': details_list[0].evMultiplier,
            'minTick': details_list[0].minTick,
            'orderTypes': details_list[0].orderTypes,
            'validExchanges': details_list[0].validExchanges,
            'priceMagnifier': details_list[0].priceMagnifier,
            'underConId': details_list[0].underConId,
            'longName': details_list[0].longName,
            'marketName': details_list[0].marketName,
        }
        
        # Add summary information
        if len(details_list) > 1:
            details_dict['contractMonth'] = ""
            # Use closest expiration as summary
            expirations = await self.get_expirations(self._contracts[ticker_id])
            if expirations:
                contract = details_dict['contracts'][-len(expirations)]
                details_dict['summary'] = vars(contract)
            else:
                details_dict['summary'] = vars(details_dict['contracts'][0])
        else:
            details_dict['summary'] = vars(details_dict['contracts'][0])
            
        # Store contract details
        self._contract_details[ticker_id] = details_dict
        
        # Add local symbol mapping
        for detail in details_list:
            contract = detail.contract
            if contract.localSymbol and contract.localSymbol not in self._local_symbol_expiry:
                self._local_symbol_expiry[contract.localSymbol] = detail.contractMonth
                
        # Add contracts to the contracts dictionary
        for contract in details_dict['contracts']:
            contract_string = self.contract_to_string(contract)
            contract_ticker_id = self.ticker_id(contract_string)
            self._contracts[contract_ticker_id] = contract
            
            # If this is a different ticker ID than the original, create a separate entry
            if contract_ticker_id != ticker_id:
                contract_details = details_dict.copy()
                contract_details['summary'] = vars(contract)
                contract_details['contracts'] = [contract]
                self._contract_details[contract_ticker_id] = contract_details
                
    def is_multi_contract(self, contract: Contract) -> bool:
        """
        Check if a contract has multiple sub-contracts with different expiries/strikes/sides.
        
        Args:
            contract: Contract to check
            
        Returns:
            True if the contract has multiple sub-contracts, False otherwise
        """
        # Futures with no expiry
        if contract.secType == "FUT" and not contract.lastTradeDateOrContractMonth:
            return True
            
        # Options with missing fields
        if contract.secType in ["OPT", "FOP"] and (
            not contract.lastTradeDateOrContractMonth or 
            not contract.strike or 
            not contract.right
        ):
            return True
            
        # Check if we have multiple contracts in the details
        ticker_id = self.ticker_id(contract)
        if ticker_id in self._contract_details and len(self._contract_details[ticker_id]["contracts"]) > 1:
            return True
            
        return False
        
    async def get_expirations(self, contract_identifier: Union[Contract, str, int], expired: int = 0) -> Tuple[int, ...]:
        """
        Get available expirations for a contract.
        
        Args:
            contract_identifier: Contract object, symbol string, or ticker ID
            expired: Number of expired contracts to include (0 = none)
            
        Returns:
            Tuple of expiration dates as integers (YYYYMMDD)
        """
        if isinstance(contract_identifier, Contract):
            ticker_id = self.ticker_id(contract_identifier)
        else:
            if isinstance(contract_identifier, int) or (
                isinstance(contract_identifier, str) and contract_identifier.isdigit()
            ):
                ticker_id = int(contract_identifier)
            else:
                ticker_id = self.ticker_id(contract_identifier)
                
        details = self.contract_details(ticker_id)
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
        
    async def get_strikes(self, contract_identifier: Union[Contract, str, int], 
                         smin: Optional[float] = None, smax: Optional[float] = None) -> Tuple[float, ...]:
        """
        Get available strikes for an option contract.
        
        Args:
            contract_identifier: Contract object, symbol string, or ticker ID
            smin: Minimum strike price
            smax: Maximum strike price
            
        Returns:
            Tuple of strike prices
        """
        if isinstance(contract_identifier, Contract):
            ticker_id = self.ticker_id(contract_identifier)
        else:
            if isinstance(contract_identifier, int) or (
                isinstance(contract_identifier, str) and contract_identifier.isdigit()
            ):
                ticker_id = int(contract_identifier)
            else:
                ticker_id = self.ticker_id(contract_identifier)
                
        details = self.contract_details(ticker_id)
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
        
    # Contract creation convenience methods
    
    async def create_stock_contract(self, symbol: str, currency: str = "USD", 
                                  exchange: str = "SMART") -> Contract:
        """
        Create a stock contract.
        
        Args:
            symbol: Stock symbol
            currency: Currency code
            exchange: Exchange code
            
        Returns:
            Stock contract object
        """
        contract_tuple = (symbol, "STK", exchange, currency, "", 0.0, "")
        return await self.create_contract(contract_tuple)
        
    async def create_futures_contract(self, symbol: str, currency: str = "USD", 
                                    expiry: Union[str, List[str]] = None,
                                    exchange: str = "GLOBEX", multiplier: str = "") -> Union[Contract, List[Contract]]:
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
            return await self.create_continuous_futures_contract(symbol[1:], exchange)
            
        # Handle multiple expiries
        expiries = [expiry] if expiry and not isinstance(expiry, list) else expiry
        
        if not expiries:
            contract_tuple = (symbol, "FUT", exchange, currency, "", 0.0, "", multiplier)
            return await self.create_contract(contract_tuple)
            
        contracts = []
        for fut_expiry in expiries:
            contract_tuple = (symbol, "FUT", exchange, currency, fut_expiry, 0.0, "", multiplier)
            contract = await self.create_contract(contract_tuple)
            contracts.append(contract)
            
        return contracts[0] if len(contracts) == 1 else contracts
        
    async def create_continuous_futures_contract(self, symbol: str, exchange: str = "GLOBEX",
                                              output: str = "contract", is_retry: bool = False) -> Union[Contract, Tuple]:
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
        contfut_contract = await self.create_contract((symbol, "CONTFUT", exchange, "", "", "", ""))
        
        # Wait for contract details
        for _ in range(25):
            await asyncio.sleep(0.01)
            contfut = self.contract_details(contfut_contract)
            if contfut.get("tickerId", 0) != 0 and contfut.get("conId", 0) != 0:
                break
                
        # Can't find contract? Retry once
        if contfut.get("conId", 0) == 0:
            if not is_retry:
                return await self.create_continuous_futures_contract(symbol, exchange, output, True)
            raise ValueError(f"Can't find a valid Contract using this combination ({symbol}/{exchange})")
            
        # Get contract details
        ticker_id = contfut.get("tickerId")
        expiry = contfut.get("contractMonth", "")
        currency = contfut.get("summary", {}).get("currency", "USD")
        multiplier = contfut.get("summary", {}).get("multiplier", "")
        
        # Delete continuous placeholder
        if ticker_id in self._contracts:
            del self._contracts[ticker_id]
        if ticker_id in self._contract_details:
            del self._contract_details[ticker_id]
            
        # Return tuple or contract
        if output == "tuple":
            return (symbol, "FUT", exchange, currency, expiry, 0.0, "", multiplier)
            
        return await self.create_futures_contract(symbol, currency, expiry, exchange, multiplier)
        
    async def create_option_contract(self, symbol: str, expiry: Union[str, List[str]] = None,
                                  strike: Union[float, List[float]] = 0.0, otype: Union[str, List[str]] = "CALL",
                                  currency: str = "USD", sec_type: str = "OPT", 
                                  exchange: str = "SMART") -> Union[Contract, List[Contract]]:
        """
        Create an option contract.
        
        Args:
            symbol: Underlying symbol
            expiry: Expiry date(s) in YYYYMMDD format
            strike: Strike price(s)
            otype: Option type(s) ('CALL' or 'PUT')
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
                for opt_otype in otypes or ["CALL"]:
                    contract_tuple = (symbol, sec_type, exchange, currency, opt_expiry, opt_strike, opt_otype)
                    contract = await self.create_contract(contract_tuple)
                    contracts.append(contract)
                    
        return contracts[0] if len(contracts) == 1 else contracts
        
    async def create_forex_contract(self, symbol: str, currency: str = "USD", 
                                 exchange: str = "IDEALPRO") -> Contract:
        """
        Create a forex contract.
        
        Args:
            symbol: Currency symbol (e.g., 'EUR' for EUR/USD)
            currency: Quote currency
            exchange: Exchange code
            
        Returns:
            Forex contract object
        """
        contract_tuple = (symbol, "CASH", exchange, currency, "", 0.0, "")
        return await self.create_contract(contract_tuple)
        
    async def create_index_contract(self, symbol: str, currency: str = "USD", 
                                 exchange: str = "CBOE") -> Contract:
        """
        Create an index contract.
        
        Args:
            symbol: Index symbol
            currency: Currency code
            exchange: Exchange code
            
        Returns:
            Index contract object
        """
        contract_tuple = (symbol, "IND", exchange, currency, "", 0.0, "")
        return await self.create_contract(contract_tuple)
        
    async def create_combo_leg(self, contract: Contract, action: str, 
                            ratio: int = 1, exchange: Optional[str] = None) -> ComboLeg:
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
            con_id = self.get_con_id(contract)
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
        
    async def create_combo_contract(self, symbol: str, legs: List[ComboLeg], 
                                 currency: str = "USD", exchange: Optional[str] = None) -> Contract:
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
        contract_tuple = (symbol, "BAG", exchange, currency, "", 0.0, "")
        return await self.create_contract(contract_tuple, combo_legs=legs)