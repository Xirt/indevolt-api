"""Scenarios for identifying device generations from model information."""

import pytest

from indevolt_api import IndevoltAPI

from ..helpers import MockDevice

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("model", "generation"),
    [
        pytest.param("CMS-SP2000", 2, id="sp2000"),
        pytest.param("CMS-SF2000", 2, id="sf2000"),
        pytest.param("CMS-SP3000", 2, id="sp3000"),
        pytest.param("CMS-SF3000", 2, id="sf3000"),
        pytest.param("CMS-SF1200", 2, id="sf1200"),
        pytest.param("BK1600", 1, id="gen1"),
        pytest.param("unknown-model", 1, id="unknown-currently-gen1"),
    ],
)
async def test_get_config_detects_generation(
    api: IndevoltAPI, device: MockDevice, model: str, generation: int
) -> None:
    """The current model mapping enriches configuration without losing fields."""
    device.response_data = {
        "device": {"type": model, "sn": "test-serial", "generation": 99},
        "network": {"ip": "192.0.2.1"},
    }

    assert await api.get_config() == {
        "device": {"type": model, "sn": "test-serial", "generation": generation},
        "network": {"ip": "192.0.2.1"},
    }

    (request,) = device.requests
    assert request.method == "GET"
    assert request.path == "/rpc/Sys.GetConfig"
    assert request.query == {}
    assert request.headers["Connection"] == "close"
    assert request.body == b""
