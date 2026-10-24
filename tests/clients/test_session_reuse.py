"""Scenarios for reusing a caller-owned session across device clients."""

import pytest
from aiohttp import ClientSession

from indevolt_api import IndevoltAPI, IndevoltBattery

from ..helpers import MockDevice

pytestmark = pytest.mark.asyncio


async def test_probe_and_polling_clients_share_session(
    device: MockDevice, session: ClientSession
) -> None:
    """A probe client and a subsequent polling client can reuse one session."""
    probe = IndevoltAPI(device.host, device.port, session)
    device.response_data = {"device": {"type": "CMS-SF2000", "sn": "test-serial"}}

    assert await probe.get_config() == {
        "device": {"type": "CMS-SF2000", "sn": "test-serial", "generation": 2}
    }

    poller = IndevoltAPI(device.host, device.port, session)
    assert await poller.get_config() == {
        "device": {"type": "CMS-SF2000", "sn": "test-serial", "generation": 2}
    }
    device.response_data = {"6002": 55}
    assert await poller.fetch_data([IndevoltBattery.SOC]) == {"6002": 55}

    assert [request.path for request in device.requests] == [
        "/rpc/Sys.GetConfig",
        "/rpc/Sys.GetConfig",
        "/rpc/Indevolt.GetData",
    ]
    assert probe.session is poller.session is session
    assert session.closed is False
