"""
ezib_async - Asynchronous Python wrapper for Interactive Brokers API.
"""

from .version import __version__
from .client import ezIBAsync
from .connection import ConnectionManager

# Export main classes for easy import
__all__ = [
    "ezIBAsync",
    "ConnectionManager",
    "__version__",
]