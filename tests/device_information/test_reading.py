"""Scenarios for reading device information, incomplete metadata and failures."""

import asyncio
import json
from unittest.mock import patch

import pytest
from aiohttp import ClientConnectionError, ClientError, ContentTypeError

from indevolt_api import IndevoltAPI

from ..helpers import MockDevice

pytestmark = pytest.mark.asyncio


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
