"""Indevolt API - Python client for Indevolt devices."""

from .client import (
    ActiveDiscoveryProtocol,
    DiscoveredDevice,
    IndevoltAPI,
    PassiveDiscoveryProtocol,
    PowerExceedsMaxError,
    SocBelowMinimumError,
    async_discover,
)
from .const import (
    ACTIVE_DISCOVERY_MESSAGE,
    ACTIVE_DISCOVERY_PORT,
    ACTIVE_DISCOVERY_TIMEOUT,
    DEVICE_LIMITS,
    PASSIVE_DISCOVERY_BIND_ADDR,
    PASSIVE_DISCOVERY_MAGIC,
    PASSIVE_DISCOVERY_PORT,
    SET_REALTIME_ACTION,
    IndevoltBattery,
    IndevoltConfig,
    IndevoltEnergyMode,
    IndevoltGrid,
    IndevoltRealtimeAction,
    IndevoltSolar,
    IndevoltSystem,
)

__version__ = "1.8.1"

__all__ = [
    "IndevoltAPI",
    "ActiveDiscoveryProtocol",
    "DiscoveredDevice",
    "PassiveDiscoveryProtocol",
    "ACTIVE_DISCOVERY_MESSAGE",
    "ACTIVE_DISCOVERY_PORT",
    "ACTIVE_DISCOVERY_TIMEOUT",
    "DEVICE_LIMITS",
    "PASSIVE_DISCOVERY_BIND_ADDR",
    "PASSIVE_DISCOVERY_MAGIC",
    "PASSIVE_DISCOVERY_PORT",
    "SET_REALTIME_ACTION",
    "IndevoltBattery",
    "IndevoltConfig",
    "IndevoltEnergyMode",
    "IndevoltGrid",
    "IndevoltRealtimeAction",
    "IndevoltSolar",
    "IndevoltSystem",
    "PowerExceedsMaxError",
    "SocBelowMinimumError",
    "async_discover",
]
