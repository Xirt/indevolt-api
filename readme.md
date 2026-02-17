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

## Device Discovery

The library supports automatic discovery of Indevolt devices on your local network using UDP broadcast.

### Quick Discovery Example

```python
import asyncio
import aiohttp
from indevolt_api import async_discover, IndevoltAPI

async def main():
    # Discover devices on the network (overrides default 5-second timeout)
    devices = await async_discover(timeout=3.0)

    if not devices:
        print("No devices found")
        return

    print(f"Found {len(devices)} device(s):")
    for device in devices:
        print(f"  - {device.host}:{device.port} (name: {device.name})")

    # Connect to the first discovered device
    async with aiohttp.ClientSession() as session:
        api = IndevoltAPI.from_discovered_device(devices[0], session)
        config = await api.get_config()
        print(f"Device config: {config}")

asyncio.run(main())
```

### Discovery Details

The discovery mechanism:

1. Sends AT command `AT+IGDEVICEIP` via UDP broadcast to `255.255.255.255:8099`
2. Indevolt devices on the same network respond to local port `10000` with their IP
3. Returns a list of `DiscoveredDevice` objects with device information

**Note:** Ensure your device and computer are on the same local network and that UDP port 10000 is available.

## API Reference

### IndevoltAPI

#### `__init__(host: str, port: int, session: aiohttp.ClientSession, timeout: float = 10.0)`

Initialize the API client.

**Parameters:**

- `host` (str): Device hostname or IP address
- `port` (int): Device port number (typically 80 or 8080)
- `session` (aiohttp.ClientSession): An aiohttp client session
- `timeout` (float): Request timeout in seconds (default: 10.0)

**Example:**

```python
# Default 10-second timeout (recommended for local devices)
api = IndevoltAPI(host="192.168.1.100", port=8080, session=session)

# Custom timeout
api = IndevoltAPI(host="192.168.1.100", port=8080, session=session, timeout=15.0)
```

#### `classmethod from_discovered_device(device: DiscoveredDevice, session: aiohttp.ClientSession, timeout: float = 10.0)`

Create an API client from a discovered device.

**Parameters:**

- `device` (DiscoveredDevice): A device object returned by `async_discover()`
- `session` (aiohttp.ClientSession): An aiohttp client session
- `timeout` (float): Request timeout in seconds (default: 10.0)

**Returns:**

- IndevoltAPI instance configured for the discovered device

**Example:**

```python
devices = await async_discover()
if devices:
    api = IndevoltAPI.from_discovered_device(devices[0], session)
```

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

#### `async set_data(t: str | int, v: Any) -> bool`

Write data to the device.

**Parameters:**

- `t`: cJson point identifier (e.g., `"47015"` or `47015`)
- `v`: Value(s) to write (automatically converted to list of integers)

**Returns:**

- True on success, false otherwhise

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

### async_discover(timeout: float = 5.0) -> list[DiscoveredDevice]

Discover Indevolt devices on the local network using UDP broadcast.

**Parameters:**

- `timeout` (float): Discovery timeout in seconds (default: 5.0 for local discovery)

**Returns:**

- List of `DiscoveredDevice` objects representing found devices

**Example:**

```python
devices = await async_discover(timeout=3.0)
for device in devices:
    print(f"Found: {device.host}:{device.port}")
```

### DiscoveredDevice

Represents a discovered Indevolt device with the following attributes:

**Attributes:**

- `host` (str): Device IP address
- `port` (int): Device port number (default: 8080)
- `name` (str | None): Device name if provided in discovery response
- `metadata` (dict): Additional device information from discovery response

**Example:**

```python
device = devices[0]
print(f"Device at {device.host}:{device.port}")
if device.name:
    print(f"Name: {device.name}")
```

## Exception Handling

The library provides two custom exceptions:

### `APIException`

Raised when there's a client error during API communication (network errors, HTTP errors).

### `TimeOutException`

Raised when an API request times out (default timeout: 10 seconds).

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

**Note:** You can adjust the timeout when creating the API client:

```python
# Increase timeout if needed (e.g., for slower networks)
api = IndevoltAPI(host="192.168.1.100", port=8080, session=session, timeout=10.0)
```

## Requirements

- Python 3.11+
- aiohttp >= 3.9.0

## License

MIT License - see LICENSE file for details
