"""Fixtures for isolated HTTP and non-networked client tests."""

import json
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from unittest.mock import Mock

import pytest
import pytest_asyncio
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestServer

from indevolt_api import IndevoltAPI

from .helpers import DeviceFactory, MockDevice, RecordedRequest


@pytest_asyncio.fixture
async def device_factory() -> AsyncIterator[DeviceFactory]:
    """Serve independent devices and clean up their loopback servers."""
    async with AsyncExitStack() as stack:

        async def create_device() -> MockDevice:
            device = MockDevice()
            app = web.Application()
            app.router.add_route("*", "/{path:.*}", device.handle)
            server = await stack.enter_async_context(TestServer(app, host=device.host))
            assert server.port is not None
            device.port = server.port
            return device

        yield create_device


@pytest_asyncio.fixture
async def device(device_factory: DeviceFactory) -> MockDevice:
    """Serve a simulated device on an ephemeral loopback port."""
    return await device_factory()


@pytest_asyncio.fixture
async def session() -> AsyncIterator[ClientSession]:
    """Provide a real HTTP session with environment proxies disabled."""
    async with ClientSession(trust_env=False) as session:
        yield session


@pytest.fixture
def api(device: MockDevice, session: ClientSession) -> IndevoltAPI:
    """Point the real client at the simulated HTTP device."""
    return IndevoltAPI(device.host, device.port, session)


@pytest.fixture
def api_without_network() -> IndevoltAPI:
    """Provide a client for the synchronous parameter checks."""
    return IndevoltAPI("192.0.2.1", 8080, Mock(spec=ClientSession))


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
