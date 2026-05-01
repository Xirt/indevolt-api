"""Indevolt API - Python client for Indevolt devices."""

from .client import (
    APIException,
    ActiveDiscoveryProtocol,
    DiscoveredDevice,
    IndevoltAPI,
    PassiveDiscoveryProtocol,
    PowerExceedsMaxError,
    SocBelowMinimumError,
    TimeOutException,
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

__version__ = "1.7.0"

__all__ = [
    "IndevoltAPI",
    "APIException",
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
    "TimeOutException",
    "async_discover",
]
