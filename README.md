# ezib_async

An asynchronous Python wrapper for Interactive Brokers API based on ib_async, providing a more Pythonic and asyncio-friendly interface.

## Overview

ezib_async is a modern, asynchronous library for interacting with Interactive Brokers API. It leverages Python's asyncio capabilities to provide a more efficient, maintainable, and developer-friendly trading library.

## Features

- **Fully Asynchronous**: Built from the ground up with Python's asyncio
- **Event-Based Architecture**: Subscribe to market data and account updates

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

    # initialize ezIBAsync
    ezib = ezIBAsync()

    # connect to IB (7496/7497 = TWS, 4001 = IBGateway)
    await ezib.connectAsync(
        ibhost='127.0.0.1',
        ibport=4001,
        ibclient=0
    )
    
    print(f"Connected: {ezib.connected}")
    
    # Your trading logic here
    
    ezib.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## Requirements

- Python 3.11+
- ib_async 1.0.3+
- Interactive Brokers TWS or Gateway

## License

[MIT License](LICENSE)