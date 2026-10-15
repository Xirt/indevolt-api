"""Scenarios for real-time charge, discharge and stop commands."""

import json
from functools import partial

import pytest

from indevolt_api import IndevoltAPI

from .helpers import MockDevice

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("command", "expected_values"),
    [
        pytest.param("charge", [1, 700, 80], id="charge"),
        pytest.param("discharge", [2, 700, 20], id="discharge"),
        pytest.param("stop", [0, 0, 0], id="stop"),
    ],
)
@pytest.mark.parametrize("accepted", [True, False], ids=["accepted", "rejected"])
async def test_realtime_command(
    api: IndevoltAPI,
    device: MockDevice,
    command: str,
    expected_values: list[int],
    accepted: bool,
) -> None:
    """Commands send the correct register payload and propagate acknowledgement."""
    device.response_data = {"result": accepted}
    action = {
        "charge": partial(api.charge, 700, 80),
        "discharge": partial(api.discharge, 700, 20),
        "stop": api.stop,
    }[command]

    assert await action() is accepted

    (request,) = device.requests
    assert request.path == "/rpc/Indevolt.SetData"
    assert json.loads(request.query["config"]) == {
        "f": 16,
        "t": 47015,
        "v": expected_values,
    }


@pytest.mark.parametrize(
    ("command", "action_code"),
    [
        pytest.param("charge", 1, id="charge"),
        pytest.param("discharge", 2, id="discharge"),
    ],
)
async def test_commands_currently_send_without_limit_checks(
    api: IndevoltAPI, device: MockDevice, command: str, action_code: int
) -> None:
    """Limit checks are currently separate from sending control commands."""
    device.response_data = {"result": True}

    assert await getattr(api, command)(12000, 4) is True

    (request,) = device.requests
    assert json.loads(request.query["config"]) == {
        "f": 16,
        "t": 47015,
        "v": [action_code, 12000, 4],
    }
