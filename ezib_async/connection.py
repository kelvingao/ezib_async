"""
Asynchronous Connection Manager for Interactive Brokers TWS/Gateway.

This module provides a ConnectionManager class that handles the asynchronous
connection to Interactive Brokers TWS/Gateway using ib_insync's async capabilities.
"""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Union
from functools import partial

# Import ib_insync for Interactive Brokers API
from ib_async import IB

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages asynchronous connection to Interactive Brokers TWS/Gateway.
    
    This class provides functionality for:
    - Asynchronous connection/disconnection to IB TWS/Gateway
    - Automatic reconnection on connection loss
    - Event handler registration and management
    - Async context manager support
    
    Attributes:
        client (IB): The ib_insync IB client instance
        host (str): Host address for IB connection
        port (int): Port number for IB connection
        client_id (int): Client ID for IB connection
        is_connected (bool): Connection status
        _event_handlers (Dict): Dictionary of registered event handlers
        _reconnect_task (Optional[asyncio.Task]): Task for automatic reconnection
        _reconnect_interval (int): Seconds between reconnection attempts
        _max_reconnect_attempts (int): Maximum number of reconnection attempts
    """
    
    def __init__(
        self,
        reconnect_interval: int = 10,
        max_reconnect_attempts: int = 5,
    ):
        """
        Initialize the ConnectionManager.
        
        Args:
            reconnect_interval (int): Seconds between reconnection attempts
            max_reconnect_attempts (int): Maximum number of reconnection attempts
        """
        self.client = IB()
        self.host = ""
        self.port = 0
        self.client_id = 0
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._reconnect_task: Optional[asyncio.Task] = None
        self._connection_check_task: Optional[asyncio.Task] = None
        self._reconnect_interval = reconnect_interval
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_attempts = 0
        
    @property
    def is_connected(self) -> bool:
        """
        Check if the client is connected to IB TWS/Gateway.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.client.isConnected()
    
    async def connect(
        self, 
        host: str = '127.0.0.1', 
        port: int = 4002, 
        client_id: int = 1,
        read_only: bool = False,
        timeout: int = 20,
        auto_reconnect: bool = True
    ) -> None:
        """
        Connect to Interactive Brokers TWS/Gateway asynchronously.
        
        Args:
            host (str): Host address for IB connection
            port (int): Port number for IB connection
            client_id (int): Client ID for IB connection
            read_only (bool): Whether to connect in read-only mode
            timeout (int): Connection timeout in seconds
            auto_reconnect (bool): Whether to automatically reconnect on disconnection
            
        Raises:
            ConnectionError: If connection fails after max attempts
        """
        # Store connection parameters for potential reconnection
        self.host = host
        self.port = port
        self.client_id = client_id
        
        # Reset reconnection attempts counter
        self._reconnect_attempts = 0
        
        try:
            logger.info(f"Connecting to IB at {host}:{port} with client ID {client_id}")
            
            # Use the async connection method from ib_insync
            await self.client.connectAsync(
                host=host,
                port=port,
                clientId=client_id,
                readonly=read_only,
                timeout=timeout
            )
            
            logger.info("Successfully connected to IB")
            
            # Set up connection monitoring and auto-reconnect if enabled
            if auto_reconnect and self._reconnect_task is None:
                self._setup_connection_monitoring()
                
        except Exception as e:
            logger.error(f"Failed to connect to IB: {str(e)}")
            raise ConnectionError(f"Failed to connect to IB: {str(e)}")
    
    def _setup_connection_monitoring(self) -> None:
        """
        Set up connection monitoring and automatic reconnection.
        
        This method registers a disconnection handler and creates a task
        for automatic reconnection if the connection is lost.
        """
        # Register disconnection handler
        logger.debug("Setting up connection monitoring")
        
        # Remove any existing handler first to avoid duplicates
        if hasattr(self.client, 'disconnectedEvent'):
            try:
                self.client.disconnectedEvent -= self._handle_disconnection
            except Exception:
                pass
                
        # Register our disconnection handler
        self.client.disconnectedEvent += self._handle_disconnection
        logger.debug("Disconnection handler registered")
        
        # Also set up a periodic connection check as a fallback
        # This helps in case the disconnectedEvent doesn't fire
        if not hasattr(self, '_connection_check_task') or self._connection_check_task is None or self._connection_check_task.done():
            self._connection_check_task = asyncio.create_task(self._monitor_connection())
            self._connection_check_task.set_name("IB_Connection_Monitor")
            logger.debug("Connection monitoring task started")
    
    async def _monitor_connection(self) -> None:
        """
        Periodically check the connection status and trigger reconnection if needed.
        
        This is a fallback mechanism in case the disconnectedEvent doesn't fire.
        """
        try:
            while True:
                # Check every 5 seconds
                await asyncio.sleep(5)
                
                # If we're not connected and not already trying to reconnect
                if not self.is_connected and (self._reconnect_task is None or self._reconnect_task.done()):
                    logger.warning("Connection check detected disconnection")
                    self._handle_disconnection()
                    
        except asyncio.CancelledError:
            logger.debug("Connection monitoring task cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in connection monitoring: {str(e)}")
    
    def _handle_disconnection(self) -> None:
        """
        Handle disconnection event from IB TWS/Gateway.
        
        This method is called when the connection to IB is lost.
        It initiates the reconnection process if auto-reconnect is enabled.
        """
        logger.warning("Disconnected from IB")
        print("Disconnected from IB")
        
        # Start reconnection task if not already running
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect())
            # Name the task for better debugging
            self._reconnect_task.set_name("IB_Reconnect_Task")
    
    async def _reconnect(self) -> None:
        """
        Attempt to reconnect to IB TWS/Gateway.
        
        This method attempts to reconnect to IB using the stored connection
        parameters. It will retry up to max_reconnect_attempts times with
        reconnect_interval seconds between attempts.
        """
        try:
            while self._reconnect_attempts < self._max_reconnect_attempts:
                self._reconnect_attempts += 1
                
                logger.info(f"Reconnection attempt {self._reconnect_attempts}/{self._max_reconnect_attempts}")
                
                try:
                    # Wait before attempting to reconnect
                    await asyncio.sleep(self._reconnect_interval)
                    
                    # Check if we're already connected (might have happened through another mechanism)
                    if self.is_connected:
                        logger.info("Already reconnected, no need to continue reconnection attempts")
                        self._reconnect_attempts = 0
                        return
                    
                    # Attempt to reconnect
                    logger.debug(f"Attempting to reconnect to {self.host}:{self.port} with client ID {self.client_id}")
                    await self.client.connectAsync(
                        host=self.host,
                        port=self.port,
                        clientId=self.client_id
                    )
                    
                    # Verify the connection was successful
                    if self.is_connected:
                        logger.info("Successfully reconnected to IB")
                        self._reconnect_attempts = 0
                        return
                    else:
                        logger.warning("Connection attempt returned but is_connected is still False")
                    
                except Exception as e:
                    logger.error(f"Reconnection attempt failed: {str(e)}")
            
            logger.error(f"Failed to reconnect after {self._max_reconnect_attempts} attempts")
            # Reset reconnection attempts counter for future reconnection attempts
            self._reconnect_attempts = 0
        except asyncio.CancelledError:
            logger.info("Reconnection task was cancelled")
            raise
        finally:
            # Ensure we reset the reconnect attempts counter
            self._reconnect_attempts = 0
        
    async def disconnect(self) -> None:
        """
        Disconnect from Interactive Brokers TWS/Gateway asynchronously.
        
        This method safely disconnects from IB, cancels any ongoing reconnection
        tasks, and cleans up resources.
        """
        # Cancel any ongoing reconnection tasks
        if self._reconnect_task is not None and not self._reconnect_task.done():
            logger.debug("Cancelling reconnection task")
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                logger.debug("Reconnection task cancelled successfully")
            except Exception as e:
                logger.error(f"Error while cancelling reconnection task: {str(e)}")
            finally:
                self._reconnect_task = None
        
        # Cancel the connection monitoring task
        if hasattr(self, '_connection_check_task') and self._connection_check_task is not None and not self._connection_check_task.done():
            logger.debug("Cancelling connection monitoring task")
            self._connection_check_task.cancel()
            try:
                await self._connection_check_task
            except asyncio.CancelledError:
                logger.debug("Connection monitoring task cancelled successfully")
            except Exception as e:
                logger.error(f"Error while cancelling connection monitoring task: {str(e)}")
            finally:
                self._connection_check_task = None
        
        # Only disconnect if currently connected
        if self.is_connected:
            logger.info("Disconnecting from IB")
            
            # Unregister any event handlers to prevent memory leaks
            if hasattr(self.client, 'disconnectedEvent'):
                try:
                    self.client.disconnectedEvent -= self._handle_disconnection
                except Exception as e:
                    logger.debug(f"Error while unregistering disconnection handler: {str(e)}")
            
            try:
                # IB's disconnect method is synchronous, run it in an executor to avoid blocking
                # loop = asyncio.get_running_loop()
                # await loop.run_in_executor(None, self.client.disconnect)
                self.client.disconnect()
                
                logger.info("Successfully disconnected from IB")
            except Exception as e:
                logger.error(f"Error during disconnection: {str(e)}")
        else:
            logger.debug("Not connected, no need to disconnect")
    
    def register_handler(self, event_name: str, handler: Callable) -> None:
        """
        Register an event handler for a specific event.
        
        Args:
            event_name (str): Name of the event to handle
            handler (Callable): Handler function to call when the event occurs
        """
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        
        if handler not in self._event_handlers[event_name]:
            self._event_handlers[event_name].append(handler)
            
            # Register with the IB client's event system
            if hasattr(self.client, event_name):
                event = getattr(self.client, event_name)
                if hasattr(event, '__iadd__'):  # Check if it's an event that can be subscribed to
                    event += handler
                    logger.debug(f"Registered handler for event: {event_name}")
    
    def unregister_handler(self, event_name: str, handler: Callable) -> None:
        """
        Unregister an event handler for a specific event.
        
        Args:
            event_name (str): Name of the event to unregister from
            handler (Callable): Handler function to unregister
        """
        if event_name in self._event_handlers and handler in self._event_handlers[event_name]:
            self._event_handlers[event_name].remove(handler)
            
            # Unregister from the IB client's event system
            if hasattr(self.client, event_name):
                event = getattr(self.client, event_name)
                if hasattr(event, '__isub__'):  # Check if it's an event that can be unsubscribed from
                    event -= handler
                    logger.debug(f"Unregistered handler for event: {event_name}")
    
    async def __aenter__(self) -> 'ConnectionManager':
        """
        Async context manager entry.
        
        Returns:
            ConnectionManager: This instance
        """
        if not self.is_connected:
            await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Async context manager exit.
        
        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        await self.disconnect()