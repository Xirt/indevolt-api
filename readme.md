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
from indevolt_api import (
    IndevoltAPI,
    IndevoltConfig,
    IndevoltEnergyMode,
    IndevoltSystem,
    SET_REALTIME_ACTION,
    IndevoltRealtimeAction,
)

async def main():
    async with aiohttp.ClientSession() as session:
        api = IndevoltAPI(host="192.168.1.100", port=8080, session=session)

        # Get device configuration
        config = await api.get_config()
        print(f"Device config: {config}")

        # Fetch data using StrEnum members — response keys are the same strings
        data = await api.fetch_data([IndevoltConfig.READ_ENERGY_MODE, IndevoltSystem.INPUT_POWER])
        print(f"Energy mode: {data[IndevoltConfig.READ_ENERGY_MODE]}")
        print(f"Input power: {data[IndevoltSystem.INPUT_POWER]}")

        # Write a single value
        await api.set_data(IndevoltConfig.WRITE_DISCHARGE_LIMIT, 50)

        # Write a real-time charge command
        await api.set_data(SET_REALTIME_ACTION, [IndevoltRealtimeAction.CHARGE, 700, 80])

asyncio.run(main())
```

## Device Discovery

The library supports two complementary discovery mechanisms.

### Active Discovery

Sends a UDP broadcast and collects replies from devices on the same network. Use `async_discover()` when you need devices immediately at startup.

```python
import asyncio
import aiohttp
from indevolt_api import async_discover, IndevoltAPI

async def main():
    # Broadcast AT+IGDEVICEIP and wait for replies (default: 5 s)
    devices = await async_discover()

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

How it works:
1. Sends `ACTIVE_DISCOVERY_MESSAGE` (`AT+IGDEVICEIP`) via UDP broadcast to `255.255.255.255:8099`
2. Devices respond to local port `ACTIVE_DISCOVERY_PORT` (`10000`) with their IP and optional metadata
3. Returns a list of `DiscoveredDevice` objects

**Note:** UDP port `10000` must be available and not blocked by a firewall.

### Passive Discovery

Listens for unsolicited broadcasts that devices emit on their own. Use `PassiveDiscoveryProtocol` for long-running applications (e.g. Home Assistant integrations) that need to detect devices as they appear without polling.

```python
import asyncio
from indevolt_api import (
    PassiveDiscoveryProtocol,
    PASSIVE_DISCOVERY_PORT,
    PASSIVE_DISCOVERY_BIND_ADDR,
)

async def main():
    seen: set[str] = set()

    def on_device_discovered(host: str) -> None:
        if host not in seen:
            seen.add(host)
            print(f"Device announced itself: {host}")

    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: PassiveDiscoveryProtocol(on_device_discovered),
        local_addr=(PASSIVE_DISCOVERY_BIND_ADDR, PASSIVE_DISCOVERY_PORT),
    )

    try:
        await asyncio.Event().wait()  # run until cancelled
    finally:
        transport.close()

asyncio.run(main())
```

How it works:
1. Devices periodically broadcast a `BCF-D`-prefixed UDP packet on port `8099`
2. `PassiveDiscoveryProtocol` filters packets by the `PASSIVE_DISCOVERY_MAGIC` prefix and invokes your callback with the sender's IP
3. No outbound traffic is sent

**Note:** Bind to `PASSIVE_DISCOVERY_BIND_ADDR` (`0.0.0.0`) so the socket accepts broadcasts on all interfaces.

### Discovery Examples

See [`examples/active_discovery_example.py`](examples/active_discovery_example.py) and [`examples/passive_discovery_example.py`](examples/passive_discovery_example.py) for runnable examples.

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

- `t`: A `StrEnum` member, a raw string key, or a list of either

**Returns:**

- Dictionary whose keys are strings matching the requested cJson points. `StrEnum` members can be used directly to index the result.

**Example:**

```python
from indevolt_api import IndevoltSystem, IndevoltGrid, IndevoltBattery

# Single point
data = await api.fetch_data(IndevoltBattery.SOC)
print(data[IndevoltBattery.SOC])

# Multiple points
data = await api.fetch_data([
    IndevoltSystem.INPUT_POWER,
    IndevoltSystem.OUTPUT_POWER,
    IndevoltGrid.VOLTAGE,
])
print(data[IndevoltSystem.INPUT_POWER])
print(data[IndevoltGrid.VOLTAGE])
```

#### `async set_data(t: str | int, v: Any) -> bool`

Write data to the device.

**Parameters:**

- `t`: cJson point identifier (e.g., `"47015"` or `47015`)
- `v`: Value(s) to write (automatically converted to list of integers)

**Returns:**

- `True` on success, `False` otherwise

**Example:**

```python
from indevolt_api import IndevoltConfig, IndevoltEnergyMode, SET_REALTIME_ACTION, IndevoltRealtimeAction

# Single value
await api.set_data(IndevoltConfig.WRITE_DISCHARGE_LIMIT, 50)

# Real-time command with multiple values
await api.set_data(SET_REALTIME_ACTION, [IndevoltRealtimeAction.CHARGE, 700, 80])

# Set energy mode
await api.set_data(IndevoltConfig.WRITE_ENERGY_MODE, IndevoltEnergyMode.SELF_CONSUMED_PRIORITIZED)
```

#### `async stop() -> bool`

Stop any active real-time charge or discharge action.

**Returns:**

- `True` on success, `False` if the command was rejected or a connection error occurred

**Example:**

```python
succeeded = await api.stop()
```

#### `async charge(power: int, target_soc: int) -> bool`

Send a real-time charge command to the device.

**Parameters:**

- `power` (int): Charge power in watts
- `target_soc` (int): Target state of charge percentage

**Returns:**

- `True` on success, `False` if the command was rejected or a connection error occurred

**Example:**

```python
succeeded = await api.charge(power=700, target_soc=80)
```

#### `async discharge(power: int, target_soc: int) -> bool`

Send a real-time discharge command to the device.

**Parameters:**

- `power` (int): Discharge power in watts
- `target_soc` (int): Target state of charge percentage

**Returns:**

- `True` on success, `False` if the command was rejected or a connection error occurred

**Example:**

```python
succeeded = await api.discharge(power=400, target_soc=20)
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

#### `check_charge_limits(power: int, target_soc: int, generation: int) -> None`

Check that charge parameters do not exceed device limits. Raises an exception if any boundary is violated.

**Parameters:**

- `power` (int): Requested charge power in watts
- `target_soc` (int): Target state of charge percentage
- `generation` (int): Device hardware generation (`1` or `2`), available from `get_config()` under `device.generation`

**Raises:**

- `PowerExceedsMaxError`: If `power` exceeds the maximum for the given generation
- `SocBelowMinimumError`: If `target_soc` is below the minimum SOC (5%)

**Example:**

```python
config = await api.get_config()
generation = config["device"]["generation"]

try:
    api.check_charge_limits(power=1000, target_soc=80, generation=generation)
except PowerExceedsMaxError as e:
    print(f"Power {e.power}W exceeds max {e.max_power}W for gen {e.generation}")
except SocBelowMinimumError as e:
    print(f"Target SOC {e.target_soc}% is below minimum {e.minimum_soc}%")
```

#### `check_discharge_limits(power: int, target_soc: int, generation: int) -> None`

Check that discharge parameters do not exceed device limits. Raises an exception if any boundary is violated.

**Parameters:**

- `power` (int): Requested discharge power in watts
- `target_soc` (int): Target state of charge percentage
- `generation` (int): Device hardware generation (`1` or `2`), available from `get_config()` under `device.generation`

**Raises:**

- `PowerExceedsMaxError`: If `power` exceeds the maximum for the given generation
- `SocBelowMinimumError`: If `target_soc` is below the minimum SOC (5%)

**Example:**

```python
config = await api.get_config()
generation = config["device"]["generation"]

try:
    api.check_discharge_limits(power=600, target_soc=10, generation=generation)
except PowerExceedsMaxError as e:
    print(f"Power {e.power}W exceeds max {e.max_power}W for gen {e.generation}")
except SocBelowMinimumError as e:
    print(f"Target SOC {e.target_soc}% is below minimum {e.minimum_soc}%")
```

### `async_discover(timeout: float = 5.0) -> list[DiscoveredDevice]`

Discover Indevolt devices on the local network using UDP broadcast.

**Parameters:**

- `timeout` (float): Discovery timeout in seconds (default: 3.0)

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

The library raises standard exceptions for network/HTTP errors, and custom exceptions for limit violations.

### `TimeoutError`

Built-in Python exception raised when an API request exceeds the configured timeout (default: 10 seconds).

### `aiohttp.ClientError`

Raised on network errors or non-200 HTTP responses during API communication.

### `PowerExceedsMaxError`

Raised by `check_charge_limits()` or `check_discharge_limits()` when the requested power exceeds the device maximum.

**Attributes:** `power`, `max_power`, `generation`

### `SocBelowMinimumError`

Raised by `check_charge_limits()` or `check_discharge_limits()` when the target SOC is below the hard minimum of 5%.

**Attributes:** `target_soc`, `minimum_soc`

**Example:**

```python
import aiohttp
from indevolt_api import IndevoltAPI

try:
    data = await api.fetch_data("7101")
except TimeoutError:
    print("Request timed out")
except aiohttp.ClientError as e:
    print(f"Network/HTTP error: {e}")
```

**Note:** You can adjust the timeout when creating the API client:

```python
# Increase timeout if needed (e.g., for slower networks)
api = IndevoltAPI(host="192.168.1.100", port=8080, session=session, timeout=10.0)
```

## Constants and Enums

All register keys and action values are available as typed `StrEnum` classes, importable directly from `indevolt_api`. Because `StrEnum` members are strings, they can be passed directly to `fetch_data()` and `set_data()`, and used to index the response dictionary — no manual conversion needed.

### `IndevoltConfig`

Register keys for configurable device settings (read and write).

```python
from indevolt_api import IndevoltConfig

# Write registers
IndevoltConfig.WRITE_ENERGY_MODE      # "47005"
IndevoltConfig.WRITE_DISCHARGE_LIMIT  # "1142"
# ... and more

# Read registers
IndevoltConfig.READ_ENERGY_MODE       # "7101"
IndevoltConfig.READ_DISCHARGE_LIMIT   # "6105"
# ... and more
```

### `IndevoltRealtimeAction`

Action values for real-time control mode, used with `SET_REALTIME_ACTION`.

```python
from indevolt_api import IndevoltRealtimeAction

IndevoltRealtimeAction.STOP       # "0"
IndevoltRealtimeAction.CHARGE     # "1"
IndevoltRealtimeAction.DISCHARGE  # "2"
```

### `IndevoltEnergyMode`

Energy mode values for `IndevoltConfig.WRITE_ENERGY_MODE`.

```python
from indevolt_api import IndevoltEnergyMode

IndevoltEnergyMode.OUTDOOR_PORTABLE
IndevoltEnergyMode.SELF_CONSUMED_PRIORITIZED
IndevoltEnergyMode.REAL_TIME_CONTROL
IndevoltEnergyMode.CHARGE_DISCHARGE_SCHEDULE
```

### `IndevoltBattery`, `IndevoltSystem`, `IndevoltGrid`, `IndevoltSolar`

Register key enums for reading battery, system-level, grid, and solar data points.

```python
from indevolt_api import IndevoltBattery, IndevoltSystem, IndevoltGrid, IndevoltSolar

data = await api.fetch_data([
    IndevoltBattery.SOC,
    IndevoltBattery.POWER,
    IndevoltSystem.OUTPUT_POWER,
    IndevoltGrid.METER_POWER_GEN2,
    IndevoltSolar.DC_INPUT_POWER_1,
])
```

### `SET_REALTIME_ACTION`

The register key used to send real-time charge/discharge commands to the device.

```python
from indevolt_api import SET_REALTIME_ACTION

await api.set_data(SET_REALTIME_ACTION, [IndevoltRealtimeAction.CHARGE, 700, 80])
```

### Discovery Constants

All discovery-related constants are importable from `indevolt_api`.

| Constant | Value | Description |
|---|---|---|
| `ACTIVE_DISCOVERY_PORT` | `10000` | Local port devices respond to |
| `ACTIVE_DISCOVERY_MESSAGE` | `b"AT+IGDEVICEIP"` | Broadcast payload |
| `ACTIVE_DISCOVERY_TIMEOUT` | `5.0` | Default `async_discover` timeout (seconds) |
| `PASSIVE_DISCOVERY_PORT` | `8099` | Port to bind for passive listening |
| `PASSIVE_DISCOVERY_MAGIC` | `b"BCF-D"` | Magic prefix of device broadcasts |
| `PASSIVE_DISCOVERY_BIND_ADDR` | `"0.0.0.0"` | Bind address for the passive listener |

### `DEVICE_LIMITS`

Dictionary of per-generation device limits used by `check_charge_limits()` and `check_discharge_limits()`.

```python
from indevolt_api import DEVICE_LIMITS

print(DEVICE_LIMITS[1])  # {'max_discharge_power': 800, 'max_charge_power': 1200, 'minimum_soc': 5}
print(DEVICE_LIMITS[2])  # {'max_discharge_power': 2400, 'max_charge_power': 2400, 'minimum_soc': 5}
```

## Requirements

- Python 3.11+
- aiohttp >= 3.9.0

## License

MIT License - see LICENSE file for details
