"""Scenarios for broadcast discovery orchestration and cleanup."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock, call

import pytest
import pytest_asyncio

from indevolt_api import ActiveDiscoveryProtocol, async_discover

pytestmark = pytest.mark.asyncio


@dataclass
class DiscoveryNetwork:
    """Controlled UDP transport, address resolution and discovery wait."""

    endpoint: AsyncMock
    transport: Mock
    protocol: ActiveDiscoveryProtocol
    wait: AsyncMock
    resolve: Mock


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


async def test_discovery_collects_replies(network: DiscoveryNetwork) -> None:
    """Broadcast replies are collected during the configured discovery window."""

    def receive_replies(timeout: float) -> None:
        network.protocol.datagram_received(
            b'{"name": "first", "port": 8081}', ("192.0.2.1", 10000)
        )
        network.protocol.datagram_received(b"{}", ("192.0.2.2", 10000))

    network.wait.side_effect = receive_replies

    devices = await async_discover(timeout=0.25)

    assert [(device.host, device.port, device.name) for device in devices] == [
        ("192.0.2.1", 8081, "first"),
        ("192.0.2.2", 8080, None),
    ]
    assert network.endpoint.call_args.kwargs == {
        "local_addr": ("0.0.0.0", 10000),
        "allow_broadcast": True,
    }
    network.transport.sendto.assert_called_once_with(
        b"AT+IGDEVICEIP", ("255.255.255.255", 8099)
    )
    network.wait.assert_awaited_once_with(0.25)
    network.transport.close.assert_called_once_with()


async def test_no_replies_returns_empty_list(network: DiscoveryNetwork) -> None:
    """The default five-second window may complete without finding devices."""
    assert await async_discover() == []

    network.wait.assert_awaited_once_with(5.0)
    network.transport.close.assert_called_once_with()


async def test_broadcast_targets_follow_current_address_derivation(
    network: DiscoveryNetwork,
) -> None:
    """Current subnet targets replace the last octet and exclude local-only IPs."""
    network.resolve.return_value = (
        "test-host",
        [],
        [
            "192.168.1.10",
            "192.168.1.11",
            "10.0.0.5",
            "127.0.0.1",
            "169.254.1.2",
        ],
    )

    assert await async_discover(timeout=0) == []

    network.resolve.assert_called_once_with("test-host")
    network.transport.sendto.assert_has_calls(
        [
            call(b"AT+IGDEVICEIP", ("255.255.255.255", 8099)),
            call(b"AT+IGDEVICEIP", ("192.168.1.255", 8099)),
            call(b"AT+IGDEVICEIP", ("10.0.0.255", 8099)),
        ],
        any_order=True,
    )
    assert network.transport.sendto.call_count == 3
    network.transport.close.assert_called_once_with()


async def test_bind_failure_returns_empty_list(network: DiscoveryNetwork) -> None:
    """A busy UDP listen port currently yields no discovered devices."""
    network.endpoint.side_effect = OSError("address already in use")

    assert await async_discover(timeout=0) == []

    network.transport.sendto.assert_not_called()
    network.wait.assert_not_awaited()
    network.transport.close.assert_not_called()


async def test_resolution_failure_keeps_global_broadcast(
    network: DiscoveryNetwork,
) -> None:
    """Hostname lookup failures retain the limited broadcast target."""
    network.resolve.side_effect = OSError("hostname lookup failed")

    assert await async_discover(timeout=0) == []

    network.transport.sendto.assert_called_once_with(
        b"AT+IGDEVICEIP", ("255.255.255.255", 8099)
    )
    network.transport.close.assert_called_once_with()


async def test_send_failure_does_not_stop_other_targets(
    network: DiscoveryNetwork,
) -> None:
    """One failed broadcast still allows the other targets to be attempted."""
    network.resolve.return_value = ("test-host", [], ["192.168.1.10"])
    network.transport.sendto.side_effect = [OSError("send failed"), None]

    assert await async_discover(timeout=0) == []

    network.transport.sendto.assert_has_calls(
        [
            call(b"AT+IGDEVICEIP", ("255.255.255.255", 8099)),
            call(b"AT+IGDEVICEIP", ("192.168.1.255", 8099)),
        ],
        any_order=True,
    )
    assert network.transport.sendto.call_count == 2
    network.wait.assert_awaited_once_with(0)
    network.transport.close.assert_called_once_with()


async def test_discovery_failure_closes_transport(network: DiscoveryNetwork) -> None:
    """An unexpected discovery failure returns an empty list and releases UDP."""
    network.wait.side_effect = RuntimeError("discovery failed")

    assert await async_discover(timeout=0) == []

    network.transport.close.assert_called_once_with()


async def test_cancellation_closes_transport(network: DiscoveryNetwork) -> None:
    """Cancelling active discovery propagates after releasing the transport."""
    waiting = asyncio.Event()
    release = asyncio.Event()

    async def wait_for_cancellation(timeout: float) -> None:
        waiting.set()
        await release.wait()

    network.wait.side_effect = wait_for_cancellation
    task = asyncio.create_task(async_discover())
    try:
        await asyncio.wait_for(waiting.wait(), timeout=5)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    network.transport.close.assert_called_once_with()
