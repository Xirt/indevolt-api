"""API client for HTTP communication with Indevolt devices."""

import json
from typing import Any

import aiohttp


class TimeOutException(Exception):
    """Raised when an API call times out."""


class APIException(Exception):
    """Raised on client error during API call."""


class IndevoltAPI:
    """Handle all HTTP communication with Indevolt devices."""

    def __init__(self, host: str, port: int, session: aiohttp.ClientSession) -> None:
        """Initialize the Indevolt API client.

        Args:
            host: Device hostname or IP address
            port: Device port number
            session: aiohttp ClientSession for HTTP requests
        """
        self.host = host
        self.port = port
        self.session = session
        self.base_url = f"http://{host}:{port}/rpc"
        self.timeout = aiohttp.ClientTimeout(total=60)

    async def _request(self, endpoint: str, config_data: dict[str, Any]) -> dict[str, Any]:
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

        return await self._request("Indevolt.GetData", {"t": t})

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

        return await self._request("Indevolt.SetData", {"f": 16, "t": t_int, "v": v_int})

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
                    data["device"]["generation"] = 2 if device_type in ["CMS-SP2000", "CMS-SF2000"] else 1
                
                return data

        except TimeoutError as err:
            raise TimeOutException("Sys.GetConfig Request timed out") from err
        except aiohttp.ClientError as err:
            raise APIException(f"Sys.GetConfig Network error: {err}") from err
