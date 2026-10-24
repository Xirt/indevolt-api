"""Scenarios for creating usable clients from discovered devices."""

import pytest
from aiohttp import ClientSession

from indevolt_api import DiscoveredDevice, IndevoltAPI

from ..helpers import MockDevice

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("options", "expected_timeout"),
    [
        pytest.param({}, 10.0, id="default"),
        pytest.param({"timeout": 2.5}, 2.5, id="custom"),
    ],
)
async def test_client_from_discovered_device(
    device: MockDevice,
    session: ClientSession,
    options: dict[str, float],
    expected_timeout: float,
) -> None:
    """Discovered addresses and the timeout configure a usable HTTP client."""
    discovered = DiscoveredDevice(device.host, device.port, name="test-device")
    api = IndevoltAPI.from_discovered_device(discovered, session, **options)

    assert await api.get_config() == {}

    (request,) = device.requests
    assert request.headers["Host"] == f"{device.host}:{device.port}"
    assert api.session is session
    assert api.timeout.total == expected_timeout
    assert session.closed is False
