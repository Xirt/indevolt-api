# Indevolt API

Python client library for communicating with Indevolt devices (home battery systems).

## Features

- Async/await support using aiohttp
- Fully typed with type hints
- Simple and intuitive API
- Comprehensive error handling

## Installation

```bash
pip install indevolt-api
```

## Quick Start

```python
import asyncio
import aiohttp
from indevolt_api import IndevoltAPI

async def main():
    async with aiohttp.ClientSession() as session:
        api = IndevoltAPI(host="192.168.1.100", port=8080, session=session)
        
        # Get device configuration
        config = await api.get_config()
        print(f"Device config: {config}")
        
        # Fetch data from specific cJson points
        data = await api.fetch_data(["7101", "1664"])
        print(f"Data: {data}")
        
        # Write data (single data point) to device
        response = await api.set_data("1142", 50)
        print(f"Set data response: {response}")
        
        # Write data (multiple data points) to device
        response = await api.set_data("47015", [2, 700, 5])
        print(f"Set data response: {response}")

asyncio.run(main())
```

## API Reference

### IndevoltAPI

#### `__init__(host: str, port: int, session: aiohttp.ClientSession)`

Initialize the API client.

**Parameters:**
- `host` (str): Device hostname or IP address
- `port` (int): Device port number (typically 80)
- `session` (aiohttp.ClientSession): An aiohttp client session

#### `async fetch_data(t: str | list[str]) -> dict[str, Any]`

Fetch data from the device.

**Parameters:**
- `t`: Single cJson point or list of cJson points to retrieve (e.g., `"7101"` or `["7101", "1664"]`)

**Returns:**
- Dictionary with device response containing cJson point data

**Example:**
```python
# Single point
data = await api.fetch_data("7101")

# Multiple points
data = await api.fetch_data(["7101", "1664", "7102"])
```

#### `async set_data(t: str | int, v: Any) -> dict[str, Any]`

Write data to the device.

**Parameters:**
- `t`: cJson point identifier (e.g., `"47015"` or `47015`)
- `v`: Value(s) to write (automatically converted to list of integers)

**Returns:**
- Dictionary with device response

**Example:**
```python
# Single value
await api.set_data("47016", 100)

# Multiple values
await api.set_data("47015", [2, 700, 5])

# String or int identifiers
await api.set_data(47016, "100")
```

#### `async get_config() -> dict[str, Any]`

Get system configuration from the device.

**Returns:**
- Dictionary with device system configuration

**Example:**
```python
config = await api.get_config()
print(config)
```

## Exception Handling

The library provides two custom exceptions:

### `APIException`

Raised when there's a client error during API communication (network errors, HTTP errors).

### `TimeOutException`

Raised when an API request times out (default timeout: 60 seconds).

**Example:**
```python
from indevolt_api import IndevoltAPI, APIException, TimeOutException

try:
    data = await api.fetch_data("7101")
except TimeOutException:
    print("Request timed out")
except APIException as e:
    print(f"API error: {e}")
```

## Requirements

- Python 3.11+
- aiohttp >= 3.9.0

## License

MIT License - see LICENSE file for details