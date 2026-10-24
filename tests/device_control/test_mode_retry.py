"""Scenarios for explicitly retrying a failed mode change before device control."""

import json

import pytest
from aiohttp import ClientSession

from indevolt_api import IndevoltAPI, IndevoltConfig, IndevoltEnergyMode

from ..helpers import MockDevice

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("status", "response"),
    [
        pytest.param(200, {"result": False}, id="rejected"),
        pytest.param(200, {}, id="missing-result"),
        pytest.param(503, {"result": True}, id="http-error"),
    ],
)
async def test_failed_mode_write_can_be_retried_before_control(
    api: IndevoltAPI,
    device: MockDevice,
    session: ClientSession,
    status: int,
    response: dict[str, bool],
) -> None:
    """A failed mode write allows an explicit retry on the same client."""
    device.status = status
    device.response_data = response

    assert (
        await api.set_data(
            IndevoltConfig.WRITE_ENERGY_MODE, IndevoltEnergyMode.REAL_TIME_CONTROL
        )
        is False
    )
    assert len(device.requests) == 1
    assert session.closed is False

    device.status = 200
    device.response_data = {"result": True}
    assert (
        await api.set_data(
            IndevoltConfig.WRITE_ENERGY_MODE, IndevoltEnergyMode.REAL_TIME_CONTROL
        )
        is True
    )
    assert await api.charge(700, 80) is True

    assert [json.loads(request.query["config"]) for request in device.requests] == [
        {"f": 16, "t": 47005, "v": [4]},
        {"f": 16, "t": 47005, "v": [4]},
        {"f": 16, "t": 47015, "v": [1, 700, 80]},
    ]
    assert session.closed is False
