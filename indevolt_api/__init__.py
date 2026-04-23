"""Indevolt API - Python client for Indevolt devices."""

from .client import (
    APIException,
    ChargePowerExceedsMaxError,
    DiscoveredDevice,
    DischargePowerExceedsMaxError,
    IndevoltAPI,
    MINIMUM_SOC,
    POWER_LIMITS,
    SocBelowMinimumError,
    TimeOutException,
    async_discover,
)

__version__ = "1.3.0"

__all__ = [
    "IndevoltAPI",
    "APIException",
    "ChargePowerExceedsMaxError",
    "DiscoveredDevice",
    "DischargePowerExceedsMaxError",
    "MINIMUM_SOC",
    "POWER_LIMITS",
    "SocBelowMinimumError",
    "TimeOutException",
    "async_discover",
]
