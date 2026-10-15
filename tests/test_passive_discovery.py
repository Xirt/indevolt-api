"""Scenarios for unsolicited device broadcasts."""

import pytest

from indevolt_api import PassiveDiscoveryProtocol


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"BCF-D", id="prefix-only"),
        pytest.param(b"BCF-D device-information", id="with-payload"),
        pytest.param(b"BCF-D\xff", id="binary-payload"),
    ],
)
def test_matching_broadcast_reports_sender(data: bytes) -> None:
    """A matching prefix reports the source IP without decoding the payload."""
    received: list[str] = []
    protocol = PassiveDiscoveryProtocol(received.append)

    protocol.datagram_received(data, ("192.0.2.1", 8099))

    assert received == ["192.0.2.1"]


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"BCF", id="incomplete-prefix"),
        pytest.param(b"bcf-d", id="wrong-case"),
        pytest.param(b"other-data", id="unrelated"),
    ],
)
def test_unrelated_broadcast_is_ignored(data: bytes) -> None:
    """Packets without the exact magic prefix do not trigger discovery."""
    received: list[str] = []
    protocol = PassiveDiscoveryProtocol(received.append)

    protocol.datagram_received(data, ("192.0.2.1", 8099))

    assert received == []


def test_repeated_broadcasts_each_trigger_callback() -> None:
    """Passive announcements currently have no IP deduplication."""
    received: list[str] = []
    protocol = PassiveDiscoveryProtocol(received.append)

    protocol.datagram_received(b"BCF-D", ("192.0.2.1", 8099))
    protocol.datagram_received(b"BCF-D", ("192.0.2.1", 10000))

    assert received == ["192.0.2.1", "192.0.2.1"]
