"""Scenarios for sending stop after a rejected charge or discharge command."""

import json

import pytest
from aiohttp import ClientSession

from indevolt_api import IndevoltAPI, IndevoltConfig, IndevoltEnergyMode

from ..helpers import MockDevice

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("command", "action"),
    [
        pytest.param("charge", 1, id="charge"),
        pytest.param("discharge", 2, id="discharge"),
    ],
)
async def test_rejected_control_can_be_followed_by_stop(
    api: IndevoltAPI,
    device: MockDevice,
    session: ClientSession,
    command: str,
    action: int,
) -> None:
    """A rejected command leaves the client usable for a subsequent stop."""
    device.response_data = {"result": True}
    assert (
        await api.set_data(
            IndevoltConfig.WRITE_ENERGY_MODE, IndevoltEnergyMode.REAL_TIME_CONTROL
        )
        is True
    )

    device.response_data = {"result": False}
    assert await getattr(api, command)(700, 50) is False

    device.response_data = {"result": True}
    assert await api.stop() is True

    assert [json.loads(request.query["config"]) for request in device.requests] == [
        {"f": 16, "t": 47005, "v": [4]},
        {"f": 16, "t": 47015, "v": [action, 700, 50]},
        {"f": 16, "t": 47015, "v": [0, 0, 0]},
    ]
    assert session.closed is False
