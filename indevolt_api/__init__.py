"""Indevolt API - Python client for Indevolt devices."""

from .client import (
    APIException,
    DiscoveredDevice,
    IndevoltAPI,
    PowerExceedsMaxError,
    SocBelowMinimumError,
    TimeOutException,
    async_discover,
)
from .const import (
    DEVICE_LIMITS,
    SET_REALTIME_ACTION,
    IndevoltBattery,
    IndevoltConfig,
    IndevoltEnergyMode,
    IndevoltGrid,
    IndevoltRealtimeAction,
    IndevoltSolar,
    IndevoltSystem,
)

__version__ = "1.4.0"

__all__ = [
    "IndevoltAPI",
    "APIException",
    "DiscoveredDevice",
    "DEVICE_LIMITS",
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
