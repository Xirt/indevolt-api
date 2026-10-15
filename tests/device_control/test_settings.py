"""Scenarios for writing device settings and interpreting acknowledgements."""

import asyncio
import json
from unittest.mock import patch

import pytest
from aiohttp import ClientConnectionError

from indevolt_api import IndevoltAPI, IndevoltConfig, IndevoltEnergyMode

from ..helpers import MockDevice

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("point", "value", "expected_point", "expected_values"),
    [
        pytest.param("47005", 1, 47005, [1], id="string-point-scalar"),
        pytest.param(47005, "4", 47005, [4], id="integer-point-string-value"),
        pytest.param(
            IndevoltConfig.WRITE_ENERGY_MODE,
            IndevoltEnergyMode.SELF_CONSUMED_PRIORITIZED,
            47005,
            [1],
            id="enum-point-and-value",
        ),
        pytest.param("47015", [1, "700", 80], 47015, [1, 700, 80], id="list"),
        pytest.param("47015", [], 47015, [], id="empty-list-forwarded"),
    ],
)
async def test_set_data_request(
    api: IndevoltAPI,
    device: MockDevice,
    point: str | int,
    value: int | str | list[int | str],
    expected_point: int,
    expected_values: list[int],
) -> None:
    """Writes send the numeric register and values in the RPC query."""
    device.response_data = {"result": True}

    assert await api.set_data(point, value) is True

    (request,) = device.requests
    assert request.method == "POST"
    assert request.path == "/rpc/Indevolt.SetData"
    assert json.loads(request.query["config"]) == {
        "f": 16,
        "t": expected_point,
        "v": expected_values,
    }
    assert request.headers["Connection"] == "close"
    assert request.body == b""


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        pytest.param({"result": True}, True, id="accepted"),
        pytest.param({"result": False}, False, id="rejected"),
        pytest.param({}, False, id="missing-result"),
        pytest.param({"result": 1}, True, id="numeric-success"),
        pytest.param({"result": 0}, False, id="numeric-failure"),
        pytest.param({"result": None}, False, id="null-result"),
    ],
)
async def test_write_result(
    api: IndevoltAPI,
    device: MockDevice,
    response: dict[str, bool | int | None],
    expected: bool,
) -> None:
    """Acknowledgements currently use the truth value of result."""
    device.response_data = response

    assert await api.set_data("47005", 1) is expected


@pytest.mark.parametrize("status", [404, 500], ids=["not-found", "server-error"])
async def test_http_error_returns_false(
    api: IndevoltAPI, device: MockDevice, status: int
) -> None:
    """Writes currently turn HTTP errors into False."""
    device.status = status

    assert await api.set_data("47005", 1) is False


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(ClientConnectionError("connection lost"), id="connection"),
        pytest.param(OSError("socket failed"), id="socket"),
        pytest.param(TimeoutError("request timed out"), id="timeout"),
    ],
)
async def test_network_failure_returns_false(
    api: IndevoltAPI, error: Exception
) -> None:
    """Communication failures are swallowed by the current write API."""
    with patch.object(api.session, "post", side_effect=error):
        assert await api.set_data("47005", 1) is False


@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        pytest.param("not-json", "application/json", id="invalid-json"),
        pytest.param('{"result": true}', "text/plain", id="wrong-content-type"),
    ],
)
async def test_invalid_response_returns_false(
    api: IndevoltAPI, device: MockDevice, body: str, content_type: str
) -> None:
    """JSON decoding and content type errors currently reject the write."""
    device.body = body
    device.content_type = content_type

    assert await api.set_data("47005", 1) is False


@pytest.mark.parametrize(
    ("point", "value"),
    [
        pytest.param("invalid", 1, id="invalid-point"),
        pytest.param("47005", "invalid", id="invalid-scalar-value"),
        pytest.param("47015", [1, "invalid", 80], id="invalid-list-value"),
    ],
)
async def test_invalid_input_raises_before_request(
    api: IndevoltAPI,
    device: MockDevice,
    point: str,
    value: int | str | list[int | str],
) -> None:
    """Numeric conversion currently happens outside write error handling."""
    with pytest.raises(ValueError):
        await api.set_data(point, value)

    assert device.requests == []


async def test_cancellation_propagates(api: IndevoltAPI) -> None:
    """Cancellation must not become a failed acknowledgement."""
    with patch.object(api.session, "post", side_effect=asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):
            await api.set_data("47005", 1)
