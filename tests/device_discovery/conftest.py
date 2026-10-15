"""Fixtures for device discovery responses and controlled UDP communication."""

import asyncio
from collections.abc import Callable
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from indevolt_api import ActiveDiscoveryProtocol

from .helpers import DiscoveryNetwork


@pytest.fixture
def protocol() -> ActiveDiscoveryProtocol:
    """Provide a fresh discovery response collector."""
    return ActiveDiscoveryProtocol()


@pytest_asyncio.fixture
async def network(monkeypatch: pytest.MonkeyPatch) -> DiscoveryNetwork:
    """Replace network boundaries while keeping the discovery protocol real."""
    network = DiscoveryNetwork(
        endpoint=AsyncMock(),
        transport=Mock(spec=asyncio.DatagramTransport),
        protocol=ActiveDiscoveryProtocol(),
        wait=AsyncMock(),
        resolve=Mock(return_value=("test-host", [], [])),
    )

    def open_endpoint(
        factory: Callable[[], ActiveDiscoveryProtocol], **options: object
    ) -> tuple[Mock, ActiveDiscoveryProtocol]:
        network.protocol = factory()
        network.protocol.connection_made(network.transport)
        return network.transport, network.protocol

    network.endpoint.side_effect = open_endpoint
    monkeypatch.setattr(
        asyncio.get_running_loop(), "create_datagram_endpoint", network.endpoint
    )
    monkeypatch.setattr("indevolt_api.client.asyncio.sleep", network.wait)
    monkeypatch.setattr("socket.gethostname", lambda: "test-host")
    monkeypatch.setattr("socket.gethostbyname_ex", network.resolve)
    return network
