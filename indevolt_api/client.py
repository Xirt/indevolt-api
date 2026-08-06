"""API client for HTTP communication with Indevolt devices."""

import asyncio
import json
import logging
from typing import Any, Callable

import aiohttp
from aiohttp import ClientError

from .const import (
    ACTIVE_DISCOVERY_MESSAGE,
    ACTIVE_DISCOVERY_PORT,
    ACTIVE_DISCOVERY_TIMEOUT,
    DEVICE_LIMITS,
    IndevoltRealtimeAction,
    PASSIVE_DISCOVERY_MAGIC,
    SET_REALTIME_ACTION,
    _ACTIVE_BROADCAST_ADDR,
)

_LOGGER = logging.getLogger(__name__)


class PowerExceedsMaxError(Exception):
    """Raised when requested (dis)charge power exceeds the device maximum."""

    def __init__(self, power: int, max_power: int, generation: int) -> None:
        self.power = power
        self.max_power = max_power
        self.generation = generation


class SocBelowMinimumError(Exception):
    """Raised when target SOC is below the API's hard minimum."""

    def __init__(self, target_soc: int, minimum_soc: int, generation: int) -> None:
        self.target_soc = target_soc
        self.minimum_soc = minimum_soc
        self.generation = generation


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


class PassiveDiscoveryProtocol(asyncio.DatagramProtocol):
    """Listens passively for unsolicited device broadcasts on UDP port 8099.

    Devices periodically broadcast a ``BCF-D``-prefixed packet on the local
    network.  Bind this protocol to :data:`~indevolt_api.PASSIVE_DISCOVERY_PORT`
    (``8099``) to receive those announcements without sending any traffic.
    """

    MAGIC: bytes = PASSIVE_DISCOVERY_MAGIC

    def __init__(self, callback: Callable[[str], None]) -> None:
        """Initialize the passive discovery protocol.

        Args:
            callback: Callable invoked with the device's IP address whenever a
                valid broadcast is received.
        """
        self._callback = callback

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Handle an incoming UDP datagram.

        Ignores packets that do not start with :data:`~indevolt_api.PASSIVE_DISCOVERY_MAGIC`.

        Args:
            data: Raw bytes received.
            addr: Sender address as ``(host, port)``.
        """
        if data.startswith(self.MAGIC):
            self._callback(addr[0])


class ActiveDiscoveryProtocol(asyncio.DatagramProtocol):
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


async def async_discover(
    timeout: float = ACTIVE_DISCOVERY_TIMEOUT,
) -> list[DiscoveredDevice]:
    """Discover Indevolt devices on the local network.

    Sends :data:`~indevolt_api.ACTIVE_DISCOVERY_MESSAGE` (``AT+IGDEVICEIP``) via
    UDP broadcast to :data:`~indevolt_api.PASSIVE_DISCOVERY_PORT` (``8099``).
    Devices on the same network will respond to :data:`~indevolt_api.ACTIVE_DISCOVERY_PORT`
    (``10000``) with their IP and optional metadata (port, name, etc.) in JSON format.

    The broadcast is sent to the subnet broadcast address of every local interface
    in addition to ``255.255.255.255``, so the packet reliably reaches the physical
    network even when virtual adapters (e.g. Docker) alter OS broadcast routing.

    Args:
        timeout: Discovery timeout in seconds (default: 5.0)

    Returns:
        List of discovered devices

    Example:
        >>> devices = await async_discover(timeout=3.0)
        >>> for device in devices:
        ...     print(f"Found device at {device.host}:{device.port}")
    """
    import socket as _socket

    loop = asyncio.get_running_loop()
    protocol = ActiveDiscoveryProtocol()

    try:
        transport, _ = await loop.create_datagram_endpoint(
            lambda: protocol,
            local_addr=("0.0.0.0", ACTIVE_DISCOVERY_PORT),
            allow_broadcast=True,
        )
    except OSError as e:
        _LOGGER.error(
            "Failed to bind to discovery port %d: %s", ACTIVE_DISCOVERY_PORT, e
        )
        return []

    # Send to 255.255.255.255 AND to every local interface's subnet broadcast.
    # This ensures the packet travels over the physical NIC when Docker or other
    # virtual adapters would otherwise intercept the limited broadcast.
    broadcast_port = _ACTIVE_BROADCAST_ADDR[1]
    send_targets: set[tuple[str, int]] = {_ACTIVE_BROADCAST_ADDR}
    try:
        for ip in _socket.gethostbyname_ex(_socket.gethostname())[2]:
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                subnet_bcast = ip.rsplit(".", 1)[0] + ".255"
                send_targets.add((subnet_bcast, broadcast_port))
    except Exception:
        pass

    try:
        for target in send_targets:
            try:
                transport.sendto(ACTIVE_DISCOVERY_MESSAGE, target)
            except Exception as e:
                _LOGGER.debug("Discovery broadcast to %s failed: %s", target, e)

        await asyncio.sleep(timeout)
        return protocol.devices

    except Exception as e:
        _LOGGER.error("Indevolt device discovery failed: %s", e)
        return []

    finally:
        transport.close()


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
            async with self.session.post(
                url,
                timeout=self.timeout,
                headers={"Connection": "close"},
            ) as response:
                if response.status != 200:
                    raise ClientError(f"HTTP status error: {response.status}")
                return await response.json()

        except TimeoutError:
            raise

        except aiohttp.ClientError as err:
            raise ClientError(f"{endpoint} Network error: {err}") from err

    async def fetch_data(self, t: str | list[str]) -> dict[str, Any]:
        """Fetch raw JSON data from the device.

        Args:
            t: cJson Point(s) to retrieve. Accepts a StrEnum member, a raw string key,
               or a list of either (e.g. [IndevoltSystem.INPUT_POWER, IndevoltGrid.VOLTAGE]).

        Returns:
            Device response dictionary whose keys are strings matching the requested
            cJson Points. StrEnum members can be used directly to index the result
            (e.g. data[IndevoltSystem.INPUT_POWER]).
        """
        if not isinstance(t, list):
            t = [t]

        t_int = [int(item) for item in t]

        return await self._request("Indevolt.GetData", {"t": t_int})

    async def set_data(self, t: str | int, v: Any) -> bool:
        """Write/push data to the device.

        Args:
            t: cJson Point identifier of the API (e.g., "47015" or 47015)
            v: Value(s) to write (will be converted to list of integers if needed)

        Returns:
            True on success, False otherwise

        Example:
            await api.set_data(SET_REALTIME_ACTION, [IndevoltRealtimeAction.CHARGE, 700, 5])
            await api.set_data(IndevoltConfig.WRITE_ENERGY_MODE, IndevoltEnergyMode.SELF_CONSUMED_PRIORITIZED)
        """
        # Convert v to list if not already
        if not isinstance(v, list):
            v = [v]

        t_int = int(t)
        v_int = [int(item) for item in v]

        try:
            response = await self._request(
                "Indevolt.SetData", {"f": 16, "t": t_int, "v": v_int}
            )

            return bool(response.get("result", False))

        except (OSError, ClientError, ValueError) as err:
            _LOGGER.debug("SetData request failed for t=%s, v=%s: %s", t, v, err)
            return False

    async def stop(self) -> bool:
        """Stop any active real-time charge or discharge action.

        Returns True on success, False if the command was rejected.
        """
        return await self.set_data(
            SET_REALTIME_ACTION,
            [IndevoltRealtimeAction.STOP, 0, 0],
        )

    async def charge(self, power: int, target_soc: int) -> bool:
        """Send a real-time charge command to the device.

        Returns True on success, False if the command was rejected.
        Raises ValueError if power or target_soc are out of range.
        """
        return await self.set_data(
            SET_REALTIME_ACTION,
            [IndevoltRealtimeAction.CHARGE, power, target_soc],
        )

    async def discharge(self, power: int, target_soc: int) -> bool:
        """Send a real-time discharge command to the device.

        Returns True on success, False if the command was rejected.
        Raises ValueError if power or target_soc are out of range.
        """
        return await self.set_data(
            SET_REALTIME_ACTION,
            [IndevoltRealtimeAction.DISCHARGE, power, target_soc],
        )

    def check_charge_limits(self, power: int, target_soc: int, generation: int) -> None:
        """Check that charge parameters do not exceed device limits.

        Args:
            power: Requested charge power in watts
            target_soc: Target state of charge percentage
            generation: Device hardware generation (1 or 2)

        Raises:
            PowerExceedsMaxError: If power exceeds the device maximum
            SocBelowMinimumError: If target_soc is below the device minimum
        """
        max_power = DEVICE_LIMITS[generation]["max_charge_power"]
        if power > max_power:
            raise PowerExceedsMaxError(power, max_power, generation)

        min_soc = DEVICE_LIMITS[generation]["minimum_soc"]
        if target_soc < min_soc:
            raise SocBelowMinimumError(target_soc, min_soc, generation)

    def check_discharge_limits(
        self, power: int, target_soc: int, generation: int
    ) -> None:
        """Check that discharge parameters do not exceed device limits.

        Args:
            power: Requested discharge power in watts
            target_soc: Target state of charge percentage
            generation: Device hardware generation (1 or 2)

        Raises:
            PowerExceedsMaxError: If power exceeds the device maximum
            SocBelowMinimumError: If target_soc is below the device minimum
        """
        max_power = DEVICE_LIMITS[generation]["max_discharge_power"]
        if power > max_power:
            raise PowerExceedsMaxError(power, max_power, generation)

        min_soc = DEVICE_LIMITS[generation]["minimum_soc"]
        if target_soc < min_soc:
            raise SocBelowMinimumError(target_soc, min_soc, generation)

    async def get_config(self) -> dict[str, Any]:
        """Get system configuration from the device.

        Returns:
            Device system configuration dictionary
        """
        url = f"{self.base_url}/Sys.GetConfig"

        try:
            async with self.session.get(
                url,
                timeout=self.timeout,
                headers={
                    "Connection": "close"
                },  # prevent keep-alive reuse on embedded firmware
            ) as response:
                if response.status != 200:
                    raise ClientError(f"HTTP status error: {response.status}")
                data = await response.json()

                # Enrich response with device generation
                if "device" in data and "type" in data["device"]:
                    device_type = data["device"]["type"]
                    data["device"]["generation"] = (
                        2
                        if device_type
                        in [
                            "CMS-SP2000",
                            "CMS-SF2000",
                            "CMS-SP3000",
                            "CMS-SF3000",
                            "CMS-SF1200",
                        ]
                        else 1
                    )

                return data

        except TimeoutError as err:
            raise TimeoutError("Sys.GetConfig Request timed out") from err

        except aiohttp.ClientError as err:
            raise ClientError(f"Sys.GetConfig Network error: {err}") from err
