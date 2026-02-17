"""Example: Discover and connect to Indevolt devices on the network."""

import asyncio
import aiohttp
from indevolt_api import async_discover, IndevoltAPI


async def main():
    """Discover devices and connect to the first one found."""
    print("Discovering Indevolt devices on the network...")
    print("(This will take a few seconds)\n")

    # Discover devices with a 5-second timeout
    devices = await async_discover()

    if not devices:
        print("No devices found on the network.")
        print("\nTroubleshooting:")
        print("  1. Ensure your device is powered on and connected to WiFi")
        print("  2. Verify your computer and device are on the same network")
        print("  3. Check that UDP port 10000 is not blocked by a firewall")
        return

    # Display discovered devices
    print(f"Found {len(devices)} device(s):\n")
    for i, device in enumerate(devices, 1):
        print(f"  {i}. IP: {device.host}:{device.port}")
        if device.name:
            print(f"     Name: {device.name}")
        if device.metadata:
            print(f"     Metadata: {device.metadata}")
        print()

    # Connect to the devices
    for device in devices:

        print(f"Connecting to device at {device.host}:{device.port}...\n")

        async with aiohttp.ClientSession() as session:
            # Create API client from discovered device
            api = IndevoltAPI.from_discovered_device(device, session)

            try:
                # Get device configuration
                config = await api.get_config()
                print("Successfully connected!")
                print(f"\nDevice Configuration:")
                print(f"  {config}\n")

                # You can now use the API to interact with the device
                # Example: Fetch data
                # data = await api.fetch_data(["7101", "1664"])
                # print(f"Data: {data}")

            except Exception as e:
                print(f"Error connecting to device: {e}")


if __name__ == "__main__":
    asyncio.run(main())
