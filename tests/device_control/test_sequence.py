"""Scenarios for validating limits, selecting a mode, controlling and reading status."""

import json

import pytest
from aiohttp import ClientSession

from indevolt_api import IndevoltAPI, IndevoltConfig, IndevoltEnergyMode

from ..helpers import MockDevice

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("model", "generation", "power"),
    [
        pytest.param("BK1600", 1, 700, id="gen1"),
        pytest.param("CMS-SF2000", 2, 1500, id="gen2"),
    ],
)
@pytest.mark.parametrize(
    ("command", "action", "target_soc", "state"),
    [
        pytest.param("charge", 1, 80, 1001, id="charge"),
        pytest.param("discharge", 2, 20, 1002, id="discharge"),
    ],
)
async def test_validate_switch_mode_control_and_read_state(
    api: IndevoltAPI,
    device: MockDevice,
    session: ClientSession,
    model: str,
    generation: int,
    power: int,
    command: str,
    action: int,
    target_soc: int,
    state: int,
) -> None:
    """Device configuration supplies the limits for a mode-and-control sequence."""
    device.response_data = {"device": {"type": model, "sn": "test-serial"}}
    config = await api.get_config()
    assert config["device"]["generation"] == generation
    getattr(api, f"check_{command}_limits")(
        power, target_soc, config["device"]["generation"]
    )

    device.response_data = {"7101": 1}
    assert await api.fetch_data([IndevoltConfig.READ_ENERGY_MODE]) == {"7101": 1}

    device.response_data = {"result": True}
    assert (
        await api.set_data(
            IndevoltConfig.WRITE_ENERGY_MODE, IndevoltEnergyMode.REAL_TIME_CONTROL
        )
        is True
    )
    assert await getattr(api, command)(power, target_soc) is True

    device.response_data = {
        "7101": 4,
        "6107": state,
        "6108": target_soc,
        "6109": power,
    }
    assert await api.fetch_data(
        [
            IndevoltConfig.READ_ENERGY_MODE,
            IndevoltConfig.READ_REALTIME_STATE,
            IndevoltConfig.READ_REALTIME_TARGET_SOC,
            IndevoltConfig.READ_REALTIME_POWER_LIMIT,
        ]
    ) == {"7101": 4, "6107": state, "6108": target_soc, "6109": power}

    assert [request.path for request in device.requests] == [
        "/rpc/Sys.GetConfig",
        "/rpc/Indevolt.GetData",
        "/rpc/Indevolt.SetData",
        "/rpc/Indevolt.SetData",
        "/rpc/Indevolt.GetData",
    ]
    assert [json.loads(request.query["config"]) for request in device.requests[1:]] == [
        {"t": [7101]},
        {"f": 16, "t": 47005, "v": [4]},
        {"f": 16, "t": 47015, "v": [action, power, target_soc]},
        {"t": [7101, 6107, 6108, 6109]},
    ]
    assert session.closed is False
