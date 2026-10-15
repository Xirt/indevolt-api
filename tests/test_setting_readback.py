"""Scenarios for writing a setting and reading its corresponding status point."""

import json

import pytest

from indevolt_api import IndevoltAPI, IndevoltConfig, IndevoltEnergyMode

from .helpers import MockDevice

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("write_point", "read_point", "value", "expected_value"),
    [
        pytest.param(
            IndevoltConfig.WRITE_LIGHT,
            IndevoltConfig.READ_LIGHT,
            True,
            1,
            id="boolean-on",
        ),
        pytest.param(
            IndevoltConfig.WRITE_LIGHT,
            IndevoltConfig.READ_LIGHT,
            False,
            0,
            id="boolean-off",
        ),
        pytest.param(
            IndevoltConfig.WRITE_DISCHARGE_LIMIT,
            IndevoltConfig.READ_DISCHARGE_LIMIT,
            20,
            20,
            id="numeric-setting",
        ),
        pytest.param(
            IndevoltConfig.WRITE_ENERGY_MODE,
            IndevoltConfig.READ_ENERGY_MODE,
            IndevoltEnergyMode.REAL_TIME_CONTROL,
            4,
            id="enum-setting",
        ),
    ],
)
async def test_write_setting_then_read_status(
    api: IndevoltAPI,
    device: MockDevice,
    write_point: IndevoltConfig,
    read_point: IndevoltConfig,
    value: bool | int,
    expected_value: int,
) -> None:
    """Setting writes and subsequent reads use their distinct point identifiers."""
    device.response_data = {"result": True}
    assert await api.set_data(write_point, value) is True

    device.response_data = {str(read_point): expected_value}
    result = await api.fetch_data([read_point])

    assert result == {str(read_point): expected_value}
    assert result[read_point] == expected_value
    assert [request.path for request in device.requests] == [
        "/rpc/Indevolt.SetData",
        "/rpc/Indevolt.GetData",
    ]
    assert [json.loads(request.query["config"]) for request in device.requests] == [
        {"f": 16, "t": int(write_point), "v": [expected_value]},
        {"t": [int(read_point)]},
    ]
