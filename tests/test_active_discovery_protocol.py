"""Scenarios for parsing active discovery responses."""

import pytest

from indevolt_api import ActiveDiscoveryProtocol


@pytest.fixture
def protocol() -> ActiveDiscoveryProtocol:
    """Provide a fresh discovery response collector."""
    return ActiveDiscoveryProtocol()


def test_response_metadata(protocol: ActiveDiscoveryProtocol) -> None:
    """The sender IP and JSON metadata describe the discovered device."""
    protocol.datagram_received(
        b'{"port": 8081, "name": "test-device", "model": "CMS-SF2000"}',
        ("192.0.2.1", 10000),
    )

    (device,) = protocol.devices
    assert device.host == "192.0.2.1"
    assert device.port == 8081
    assert device.name == "test-device"
    assert device.metadata == {"model": "CMS-SF2000"}


def test_missing_metadata_uses_defaults(protocol: ActiveDiscoveryProtocol) -> None:
    """An empty JSON object still yields an address with the default port."""
    protocol.datagram_received(b"{}", ("192.0.2.1", 10000))

    (device,) = protocol.devices
    assert device.host == "192.0.2.1"
    assert device.port == 8080
    assert device.name is None
    assert device.metadata == {}


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"192.0.2.1", id="non-json"),
        pytest.param(b"\xff\xfe", id="invalid-utf8"),
    ],
)
def test_unparseable_response_falls_back_to_sender(
    protocol: ActiveDiscoveryProtocol, data: bytes
) -> None:
    """Invalid JSON or encoding currently falls back to the sender address."""
    protocol.datagram_received(data, ("192.0.2.1", 10000))

    (device,) = protocol.devices
    assert device.host == "192.0.2.1"
    assert device.port == 8080
    assert device.name is None
    assert device.metadata == {}


def test_duplicate_ip_keeps_first_response(protocol: ActiveDiscoveryProtocol) -> None:
    """Further responses from the same IP do not replace its first metadata."""
    protocol.datagram_received(b'{"name": "first"}', ("192.0.2.1", 10000))
    protocol.datagram_received(
        b'{"name": "second", "port": 9000}', ("192.0.2.1", 10001)
    )

    (device,) = protocol.devices
    assert device.name == "first"
    assert device.port == 8080


def test_different_ips_are_collected(protocol: ActiveDiscoveryProtocol) -> None:
    """Matching metadata from different IPs represents different devices."""
    protocol.datagram_received(b"{}", ("192.0.2.1", 10000))
    protocol.datagram_received(b"{}", ("192.0.2.2", 10000))

    assert [device.host for device in protocol.devices] == [
        "192.0.2.1",
        "192.0.2.2",
    ]


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"null", id="null"),
        pytest.param(b"[]", id="array"),
        pytest.param(b"1", id="number"),
        pytest.param(b'"device"', id="string"),
    ],
)
def test_non_object_json_currently_raises(
    protocol: ActiveDiscoveryProtocol, data: bytes
) -> None:
    """Valid JSON with a non-object root currently raises AttributeError."""
    with pytest.raises(AttributeError):
        protocol.datagram_received(data, ("192.0.2.1", 10000))

    assert protocol.devices == []
