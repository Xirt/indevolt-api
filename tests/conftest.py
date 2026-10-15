"""Shared HTTP devices and caller-owned sessions for SDK scenarios."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack

import pytest
import pytest_asyncio
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestServer

from indevolt_api import IndevoltAPI

from .helpers import DeviceFactory, MockDevice


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
