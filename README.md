# ezib_async

An asynchronous Python wrapper for Interactive Brokers API based on ib_async, providing a more Pythonic and asyncio-friendly interface.

## Overview

ezib_async is a modern, asynchronous library for interacting with Interactive Brokers API. It leverages Python's asyncio capabilities to provide a more efficient, maintainable, and developer-friendly trading library.

## Features

- **Fully Asynchronous**: Built from the ground up with Python's asyncio
- **Automatic Reconnection**: Handles connection drops gracefully
- **Event-Based Architecture**: Subscribe to market data and account updates
- **Context Manager Support**: Use with async context managers for clean resource management

## Installation

```bash
# Using pip
pip install ezib-async

# Using uv (recommended)
uv pip install ezib-async
```

## Quick Start

```python
import asyncio
from ezib_async import ezIBpyAsync

async def main():
    # Connect to IB Gateway/TWS
    async with ezIBpyAsync() as ib:
        # Connect to IB Gateway/TWS
        await ib.connect(
            host='127.0.0.1',
            port=4002,  # Use 4001 for Gateway, 7496 for TWS
            client_id=1
        )
        
        print(f"Connected: {ib.is_connected}")
        
        # Your trading logic here
        
        # Disconnection happens automatically when exiting the context manager

if __name__ == "__main__":
    asyncio.run(main())
```

## Requirements

- Python 3.11+
- ib_async 1.0.3+
- Interactive Brokers TWS or Gateway

## License

MIT License

## Acknowledgements

- Uses ib_async for the core async IB API functionality