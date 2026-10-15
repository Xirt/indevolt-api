"""Scenarios for distinguishing devices and ignoring duplicate discovery replies."""

from indevolt_api import ActiveDiscoveryProtocol


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
