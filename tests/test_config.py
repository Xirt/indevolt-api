"""Scenarios for system configuration and hardware generation detection."""

import asyncio
import json
from unittest.mock import patch

import pytest
from aiohttp import ClientConnectionError, ClientError, ClientSession, ContentTypeError

from indevolt_api import DiscoveredDevice, IndevoltAPI

from .helpers import MockDevice

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


@pytest.mark.parametrize(
    "config",
    [
        pytest.param({}, id="no-device"),
        pytest.param({"device": {}}, id="empty-device"),
        pytest.param({"device": {"sn": "test-serial"}}, id="no-type"),
    ],
)
async def test_config_without_model_is_returned_unchanged(
    api: IndevoltAPI, device: MockDevice, config: dict[str, object]
) -> None:
    """Missing model information currently leaves the response unchanged."""
    device.response_data = config

    assert await api.get_config() == config


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


@pytest.mark.parametrize("status", [404, 500], ids=["not-found", "server-error"])
async def test_http_error_raises(
    api: IndevoltAPI, device: MockDevice, status: int
) -> None:
    """Configuration HTTP errors include the failing endpoint."""
    device.status = status

    with pytest.raises(ClientError, match=rf"Sys\.GetConfig.*{status}"):
        await api.get_config()


async def test_connection_error_raises(api: IndevoltAPI) -> None:
    """Configuration preserves the original connection failure as its cause."""
    error = ClientConnectionError("connection lost")
    with patch.object(api.session, "get", side_effect=error):
        with pytest.raises(ClientError, match=r"Sys\.GetConfig") as exc:
            await api.get_config()

    assert exc.value.__cause__ is error


async def test_timeout_is_wrapped(api: IndevoltAPI) -> None:
    """Configuration currently adds endpoint context to timeout exceptions."""
    error = TimeoutError("request timed out")
    with patch.object(api.session, "get", side_effect=error):
        with pytest.raises(TimeoutError, match=r"Sys\.GetConfig") as exc:
            await api.get_config()

    assert exc.value.__cause__ is error


async def test_invalid_json_raises(api: IndevoltAPI, device: MockDevice) -> None:
    """Invalid configuration JSON currently propagates the decode error."""
    device.body = "not-json"

    with pytest.raises(json.JSONDecodeError):
        await api.get_config()


async def test_non_json_content_type_raises(
    api: IndevoltAPI, device: MockDevice
) -> None:
    """Configuration responses also require a JSON-compatible content type."""
    device.body = "{}"
    device.content_type = "text/plain"

    with pytest.raises(ClientError, match=r"Sys\.GetConfig") as exc:
        await api.get_config()

    assert isinstance(exc.value.__cause__, ContentTypeError)


async def test_cancellation_propagates(api: IndevoltAPI) -> None:
    """Cancellation of configuration reads is visible to the caller."""
    with patch.object(api.session, "get", side_effect=asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):
            await api.get_config()
