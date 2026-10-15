"""Scenarios for reading device data over HTTP."""

import asyncio
import json
from unittest.mock import patch

import pytest
from aiohttp import ClientConnectionError, ClientError, ContentTypeError

from indevolt_api import IndevoltAPI, IndevoltBattery, IndevoltGrid, IndevoltSystem

from .helpers import MockDevice

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("points", "expected_points"),
    [
        pytest.param("6002", [6002], id="single-string"),
        pytest.param(IndevoltBattery.SOC, [6002], id="single-enum"),
        pytest.param(["2101", "2600"], [2101, 2600], id="string-list"),
        pytest.param(
            [IndevoltSystem.AC_TOTAL_INPUT_POWER, IndevoltGrid.VOLTAGE],
            [2101, 2600],
            id="enum-list",
        ),
        pytest.param(["2101", IndevoltBattery.SOC], [2101, 6002], id="mixed-list"),
        pytest.param([], [], id="empty-list-forwarded"),
    ],
)
async def test_fetch_data_request(
    api: IndevoltAPI,
    device: MockDevice,
    points: str | list[str],
    expected_points: list[int],
) -> None:
    """Point inputs become an integer list in the RPC query parameter."""
    device.response_data = {"6002": 50}

    assert await api.fetch_data(points) == {"6002": 50}

    (request,) = device.requests
    assert request.method == "POST"
    assert request.path == "/rpc/Indevolt.GetData"
    assert json.loads(request.query["config"]) == {"t": expected_points}
    assert request.headers["Connection"] == "close"
    assert request.body == b""


async def test_fetch_data_preserves_response(
    api: IndevoltAPI, device: MockDevice
) -> None:
    """Raw values and string keys remain usable with the exported enums."""
    device.response_data = {
        "0": [65, 66],
        "6002": 50,
        "6000": -120,
        "2600": 230.5,
    }

    result = await api.fetch_data(["0", "6002", "6000", "2600"])

    assert result == device.response_data
    assert result[IndevoltBattery.SOC] == 50


@pytest.mark.parametrize(
    "points",
    [
        pytest.param("invalid", id="invalid-single-point"),
        pytest.param(["6002", "invalid"], id="invalid-point-in-list"),
    ],
)
async def test_invalid_point_raises_before_request(
    api: IndevoltAPI, device: MockDevice, points: str | list[str]
) -> None:
    """Invalid numeric point identifiers currently raise ValueError."""
    with pytest.raises(ValueError):
        await api.fetch_data(points)

    assert device.requests == []


@pytest.mark.parametrize("status", [404, 500], ids=["not-found", "server-error"])
async def test_http_error_raises(
    api: IndevoltAPI, device: MockDevice, status: int
) -> None:
    """Non-200 responses surface as endpoint-specific client errors."""
    device.status = status

    with pytest.raises(ClientError, match=rf"Indevolt\.GetData.*{status}"):
        await api.fetch_data("6002")


async def test_connection_error_raises(api: IndevoltAPI) -> None:
    """Reading preserves the original connection failure as the cause."""
    error = ClientConnectionError("connection lost")
    with patch.object(api.session, "post", side_effect=error):
        with pytest.raises(ClientError, match=r"Indevolt\.GetData") as exc:
            await api.fetch_data("6002")

    assert exc.value.__cause__ is error


async def test_timeout_propagates(api: IndevoltAPI) -> None:
    """Reading currently propagates the original timeout."""
    error = TimeoutError("request timed out")
    with patch.object(api.session, "post", side_effect=error):
        with pytest.raises(TimeoutError) as exc:
            await api.fetch_data("6002")

    assert exc.value is error


async def test_invalid_json_raises(api: IndevoltAPI, device: MockDevice) -> None:
    """A successful HTTP status does not hide invalid JSON."""
    device.body = "not-json"

    with pytest.raises(json.JSONDecodeError):
        await api.fetch_data("6002")


async def test_non_json_content_type_raises(
    api: IndevoltAPI, device: MockDevice
) -> None:
    """The reader requires a JSON-compatible response content type."""
    device.body = '{"6002": 50}'
    device.content_type = "text/plain"

    with pytest.raises(ClientError, match=r"Indevolt\.GetData") as exc:
        await api.fetch_data("6002")

    assert isinstance(exc.value.__cause__, ContentTypeError)


async def test_cancellation_propagates(api: IndevoltAPI) -> None:
    """Cancellation remains visible to the caller."""
    with patch.object(api.session, "post", side_effect=asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):
            await api.fetch_data("6002")
