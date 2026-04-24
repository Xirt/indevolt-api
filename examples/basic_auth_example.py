"""Example showing how to use HTTP DIGEST authentication with IndevoltAPI."""

import asyncio

import aiohttp

from indevolt_api import IndevoltAPI, async_discover


async def main():
    """Example with HTTP DIGEST authentication."""
    # Discover devices on the network
    devices = await async_discover()

    if not devices:
        print("No devices found")
        return

    device = devices[0]
    print(f"Found device: {device}")

    # Create a session with authentication credentials
    async with aiohttp.ClientSession() as session:
        # Create API client with HTTP DIGEST authentication
        # Provide username and password for digest auth
        api = IndevoltAPI.from_discovered_device(
            device,
            session,
            timeout=10.0,
            username="admin",
            password="password123",
        )

        # Fetch configuration (with digest auth applied)
        config = await api.get_config()
        print(f"Device config: {config}")

        # Fetch data (with digest auth applied)
        data = await api.fetch_data(["7101", "1664"])
        print(f"Device data: {data}")

        # Set data (with digest auth applied)
        result = await api.set_data("47015", [2, 700, 5])
        print(f"Data written successfully: {result}")


async def basic_usage():
    """Basic usage without authentication."""
    async with aiohttp.ClientSession() as session:
        # Create API client without authentication
        api = IndevoltAPI(
            host="192.168.1.100",
            port=8080,
            session=session,
        )

        config = await api.get_config()
        print(f"Device config: {config}")


async def direct_initialization():
    """Direct initialization with digest auth."""
    async with aiohttp.ClientSession() as session:
        # Create API client directly with digest auth
        api = IndevoltAPI(
            host="192.168.1.100",
            port=8080,
            session=session,
            username="admin",
            password="password123",
        )

        config = await api.get_config()
        print(f"Device config: {config}")


if __name__ == "__main__":
    asyncio.run(main())
