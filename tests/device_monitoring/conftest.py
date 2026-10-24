"""Mutable device snapshots for polling and recovery scenarios."""

import json

import pytest
from aiohttp import web

from ..helpers import MockDevice, RecordedRequest


@pytest.fixture
def point_values(device: MockDevice) -> dict[str, int]:
    """Serve only the requested points from a mutable device snapshot."""
    values: dict[str, int] = {}

    def respond(request: RecordedRequest) -> web.Response:
        if request.path == "/rpc/Sys.GetConfig":
            return web.json_response(device.response_data, status=device.status)
        points = json.loads(request.query["config"])["t"]
        return web.json_response(
            {str(point): values[str(point)] for point in points}, status=device.status
        )

    device.responder = respond
    return values
