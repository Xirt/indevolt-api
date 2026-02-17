"""API client for HTTP communication with Indevolt devices."""

import asyncio
import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class TimeOutException(Exception):
    """Raised when an API call times out."""


class APIException(Exception):
    """Raised on client error during API call."""


# Discovery configuration
DISCOVERY_PORT = 10000
BROADCAST_PORT = 8099
DISCOVERY_MESSAGE = b"AT+IGDEVICEIP"
DISCOVERY_TIMEOUT = 3
BROADCAST_ADDR = ("255.255.255.255", BROADCAST_PORT)


class DiscoveredDevice:
    """Represents a discovered Indevolt device."""

    def __init__(
        self, host: str, port: int = 8080, name: str | None = None, **kwargs: Any
    ) -> None:
        """Initialize discovered device.

        Args:
            host: Device IP address
            port: Device port (default: 8080)
            name: Device name if available
            **kwargs: Additional device metadata
        """
        self.host = host
        self.port = port
        self.name = name
        self.metadata = kwargs

    def __repr__(self) -> str:
        """Return string representation."""
        return f"DiscoveredDevice(host={self.host!r}, port={self.port}, name={self.name!r})"


class DeviceDiscoveryProtocol(asyncio.DatagramProtocol):
    """Protocol to handle UDP discovery responses from Indevolt devices."""

    def __init__(self) -> None:
        """Initialize discovery protocol."""
        self.transport: asyncio.transports.DatagramTransport | None = None
        self.devices: list[DiscoveredDevice] = []
        self.received_ips: set[str] = set()

    def connection_made(self, transport: asyncio.transports.BaseTransport) -> None:
        """Handle connection establishment.

        Args:
            transport: UDP transport
        """
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Handle incoming UDP datagram from device.

        Args:
            data: Received data bytes
            addr: Sender address (host, port)
        """
        host = addr[0]

        # Avoid duplicate discoveries
        if host in self.received_ips:
            return

        try:
            response = json.loads(data.decode("utf-8"))

        except (json.JSONDecodeError, UnicodeDecodeError):
            device = DiscoveredDevice(host=host)

        else:
            device = DiscoveredDevice(
                host=host,
                port=response.get("port", 8080),
                name=response.get("name"),
                **{k: v for k, v in response.items() if k not in ["port", "name"]},
            )

        self.devices.append(device)
        self.received_ips.add(host)


async def async_discover(timeout: float = DISCOVERY_TIMEOUT) -> list[DiscoveredDevice]:
    """Discover Indevolt devices on the local network.

    Sends AT command "AT+IGDEVICEIP" via UDP broadcast to port 8099.
    Devices on the same network will respond to port 10000 with their IP
    and optional metadata (port, name, etc.) in JSON format.

    Args:
        timeout: Discovery timeout in seconds (default: 5.0)

    Returns:
        List of discovered devices

    Example:
        >>> devices = await async_discover(timeout=3.0)
        >>> for device in devices:
        ...     print(f"Found device at {device.host}:{device.port}")
    """
    import socket

    loop = asyncio.get_running_loop()

    # Create UDP socket for discovery
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.bind(("0.0.0.0", DISCOVERY_PORT))

    except OSError as e:
        _LOGGER.error("Failed to bind to port %d: %s", DISCOVERY_PORT, e)
        sock.close()
        return []

    protocol = DeviceDiscoveryProtocol()

    try:
        transport, _ = await loop.create_datagram_endpoint(
            lambda: protocol,
            sock=sock,
        )

        # Send broadcast discovery message
        transport.sendto(DISCOVERY_MESSAGE, BROADCAST_ADDR)

        # Wait for responses
        await asyncio.sleep(timeout)

        # Close transport
        transport.close()

        return protocol.devices

    except Exception as e:
        _LOGGER.error("Indevolt device discovery failed: %s", e)
        return []

    finally:
        if not sock._closed:
            sock.close()


class IndevoltAPI:
    """Handle all HTTP communication with Indevolt devices."""

    def __init__(
        self,
        host: str,
        port: int,
        session: aiohttp.ClientSession,
        timeout: float = 10.0,
    ) -> None:
        """Initialize the Indevolt API client.

        Args:
            host: Device hostname or IP address
            port: Device port number
            session: aiohttp ClientSession for HTTP requests
            timeout: Request timeout in seconds (default: 10.0)
        """
        self.host = host
        self.port = port
        self.session = session
        self.base_url = f"http://{host}:{port}/rpc"
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    @classmethod
    def from_discovered_device(
        cls,
        device: DiscoveredDevice,
        session: aiohttp.ClientSession,
        timeout: float = 10.0,
    ) -> "IndevoltAPI":
        """Create API client from a discovered device.

        Args:
            device: Discovered device object
            session: aiohttp ClientSession for HTTP requests
            timeout: Request timeout in seconds (default: 10.0)

        Returns:
            IndevoltAPI instance configured for the discovered device

        Example:
            >>> devices = await async_discover()
            >>> if devices:
            ...     api = IndevoltAPI.from_discovered_device(devices[0], session)
            ...     # Or with custom timeout:
            ...     api = IndevoltAPI.from_discovered_device(devices[0], session, timeout=10.0)
        """
        return cls(host=device.host, port=device.port, session=session, timeout=timeout)

    async def _request(
        self, endpoint: str, config_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make HTTP request to device endpoint.

        Args:
            endpoint: RPC endpoint name (e.g., "Indevolt.GetData")
            config_data: Configuration data to send

        Returns:
            Device response dictionary
        """
        config_param = json.dumps(config_data).replace(" ", "")
        url = f"{self.base_url}/{endpoint}?config={config_param}"

        try:
            async with self.session.post(url, timeout=self.timeout) as response:
                if response.status != 200:
                    raise APIException(f"HTTP status error: {response.status}")
                return await response.json()

        except TimeoutError as err:
            raise TimeOutException(f"{endpoint} Request timed out") from err
        except aiohttp.ClientError as err:
            raise APIException(f"{endpoint} Network error: {err}") from err

    async def fetch_data(self, t: Any) -> dict[str, Any]:
        """Fetch raw JSON data from the device.

        Args:
            t: cJson Point(s) of the API to retrieve (e.g., ["7101", "1664"] or "7101")

        Returns:
            Device response dictionary with cJson Point data
        """
        if not isinstance(t, list):
            t = [t]
            
        t_int = [int(item) for item in t]

        return await self._request("Indevolt.GetData", {"t": t_int})

    async def set_data(self, t: str | int, v: Any) -> dict[str, Any]:
        """Write/push data to the device.

        Args:
            t: cJson Point identifier of the API (e.g., "47015" or 47015)
            v: Value(s) to write (will be converted to list of integers if needed)

        Returns:
            Device response dictionary

        Example:
            await api.set_data("47015", [2, 700, 5])
            await api.set_data("47016", 100)
            await api.set_data(47016, "100")
        """
        # Convert v to list if not already
        if not isinstance(v, list):
            v = [v]

        t_int = int(t)
        v_int = [int(item) for item in v]

        return await self._request(
            "Indevolt.SetData", {"f": 16, "t": t_int, "v": v_int}
        )

    async def get_config(self) -> dict[str, Any]:
        """Get system configuration from the device.

        Returns:
            Device system configuration dictionary
        """
        url = f"{self.base_url}/Sys.GetConfig"

        try:
            async with self.session.get(url, timeout=self.timeout) as response:
                if response.status != 200:
                    raise APIException(f"HTTP status error: {response.status}")
                data = await response.json()

                # Enrich response with device generation
                if "device" in data and "type" in data["device"]:
                    device_type = data["device"]["type"]
                    data["device"]["generation"] = (
                        2 if device_type in ["CMS-SP2000", "CMS-SF2000"] else 1
                    )

                return data

        except TimeoutError as err:
            raise TimeOutException("Sys.GetConfig Request timed out") from err
        except aiohttp.ClientError as err:
            raise APIException(f"Sys.GetConfig Network error: {err}") from err
