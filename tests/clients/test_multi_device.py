"""Scenarios for concurrent device reads and recovery with a shared session."""

import asyncio

import pytest
from aiohttp import ClientError, ClientSession

from indevolt_api import IndevoltAPI, IndevoltBattery

from ..helpers import DeviceFactory

pytestmark = pytest.mark.asyncio


async def test_multiple_devices_share_session(
    device_factory: DeviceFactory, session: ClientSession
) -> None:
    """Concurrent clients keep their device addresses and responses independent."""
    first = await device_factory()
    second = await device_factory()
    first.response_data = {"6002": 25}
    second.response_data = {"6002": 75}
    first_api = IndevoltAPI(first.host, first.port, session)
    second_api = IndevoltAPI(second.host, second.port, session)

    results = await asyncio.gather(
        first_api.fetch_data([IndevoltBattery.SOC]),
        second_api.fetch_data([IndevoltBattery.SOC]),
    )

    assert results == [{"6002": 25}, {"6002": 75}]
    assert first_api.session is second_api.session is session
    assert first.requests[0].headers["Host"] == f"{first.host}:{first.port}"
    assert second.requests[0].headers["Host"] == f"{second.host}:{second.port}"
    assert session.closed is False


async def test_device_failure_leaves_shared_session_usable(
    device_factory: DeviceFactory, session: ClientSession
) -> None:
    """One device failure leaves the other client and later retries usable."""
    failing = await device_factory()
    healthy = await device_factory()
    failing.status = 503
    failing.response_data = {"6002": 25}
    healthy.response_data = {"6002": 75}
    failing_api = IndevoltAPI(failing.host, failing.port, session)
    healthy_api = IndevoltAPI(healthy.host, healthy.port, session)

    error, data = await asyncio.gather(
        failing_api.fetch_data([IndevoltBattery.SOC]),
        healthy_api.fetch_data([IndevoltBattery.SOC]),
        return_exceptions=True,
    )

    assert isinstance(error, ClientError)
    assert "Indevolt.GetData" in str(error)
    assert data == {"6002": 75}
    assert session.closed is False

    failing.status = 200
    assert await failing_api.fetch_data([IndevoltBattery.SOC]) == {"6002": 25}
    assert await healthy_api.fetch_data([IndevoltBattery.SOC]) == {"6002": 75}
    assert len(failing.requests) == len(healthy.requests) == 2
    assert session.closed is False
