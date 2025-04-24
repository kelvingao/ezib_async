# ezIBpy_async.py
from .connection import ConnectionManager
from .contracts import ContractManager

class ezIBAsync:
    def __init__(self):
        self._conn = ConnectionManager()
        self._contracts = ContractManager(self._conn)
        # self._orders = OrderManager(self._conn, self._contracts)
        
    async def connect(
        self, host: str = '127.0.0.1', port: int = 4002, client_id: int = 1) -> None:
      
        await self._conn.connect(
            host=host, 
            port=port, 
            client_id=client_id
        )
    
    async def disconnect(self) -> None:
        await self._conn.disconnect()
    
    async def __aenter__(self):

        await self._conn.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):

        await self._conn.disconnect()
    
    @property
    def is_connected(self) -> bool:
        return self._conn.is_connected
    
    @property
    def ib(self):
        return self._conn.client
    
    @property
    def contracts(self):
        return self._contracts
    
    # @property
    # def orders(self):
    #     return self._orders