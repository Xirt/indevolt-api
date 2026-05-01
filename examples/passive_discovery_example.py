"""Example: Passive discovery — listen for unsolicited device broadcasts.

Indevolt devices periodically broadcast a BCF-D-prefixed UDP packet on the
local network.  This example binds PassiveDiscoveryProtocol to the broadcast
port and prints each new device IP as it is announced, without sending any
traffic of its own.

Usage:
    python passive_discovery_example.py

Press Ctrl+C to stop listening.
"""

import asyncio
import socket
import aiohttp
from indevolt_api import (
    IndevoltAPI,
    PassiveDiscoveryProtocol,
    PASSIVE_DISCOVERY_PORT,
    PASSIVE_DISCOVERY_BIND_ADDR,
)


async def main() -> None:
    """Listen for passive device broadcasts indefinitely."""
    print("Press Ctrl+C to stop.\n")

    seen: set[str] = set()

    def on_device_discovered(host: str) -> None:
        if host in seen:
            return
        seen.add(host)
        print(f"[passive] Device announced itself: {host}")

    loop = asyncio.get_running_loop()
    transports: list[asyncio.DatagramTransport] = []

    # On Windows, subnet-directed broadcasts (e.g. 192.168.2.255) are only
    # delivered to sockets bound to the matching interface IP, not to 0.0.0.0.
    # We bind one socket per non-loopback, non-link-local interface so that
    # broadcasts on any local network are received.
    bind_addrs = [
        ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]
        if not ip.startswith("127.") and not ip.startswith("169.254.")
    ] or [PASSIVE_DISCOVERY_BIND_ADDR]

    for bind_addr in bind_addrs:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            sock.bind((bind_addr, PASSIVE_DISCOVERY_PORT))
        except OSError as exc:
            sock.close()
            print(f"[WARN] Cannot bind to {bind_addr}:{PASSIVE_DISCOVERY_PORT}: {exc}")
            if "10013" in str(exc):
                print("       Hint: another process (e.g. Docker Desktop) may be holding this port.")
            continue

        transport, _ = await loop.create_datagram_endpoint(
            lambda: PassiveDiscoveryProtocol(on_device_discovered),
            sock=sock,
        )
        transports.append(transport)
        print(f"Listening on {bind_addr}:{PASSIVE_DISCOVERY_PORT}")

    if not transports:
        print("\n[ERROR] Could not bind on any interface. No passive listener started.")
        return

    print()
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        for t in transports:
            t.close()
        print("\nStopped passive listener.")


async def connect(host: str) -> None:
    """Optional: connect to a passively discovered device and fetch its config."""
    async with aiohttp.ClientSession() as session:
        api = IndevoltAPI(host=host, port=8080, session=session)
        try:
            config = await api.get_config()
            print(f"  [{host}] config: {config}")
        except Exception as exc:
            print(f"  [{host}] connection failed: {exc}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
