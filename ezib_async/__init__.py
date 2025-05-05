"""
ezib_async - Asynchronous Python wrapper for Interactive Brokers API.
"""

from .version import __version__
from .ezib import ezIBAsync
from .connection import ConnectionManager
# from .contracts import ContractsManager
from .account import AccountContext, PositionManager, PortfolioManager
from . import util

# Export main classes for easy import
__all__ = [
    "ezIBAsync",
    "util",
    "ConnectionManager",
    # "ContractsManager",
    "AccountContext",
    "PositionManager",
    "PortfolioManager",
    "__version__",
]