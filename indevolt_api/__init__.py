"""Indevolt API - Python client for Indevolt devices."""

from .client import (
    APIException,
    DiscoveredDevice,
    IndevoltAPI,
    MINIMUM_SOC,
    POWER_LIMITS,
    PowerExceedsMaxError,
    SocBelowMinimumError,
    TimeOutException,
    async_discover,
)

__version__ = "1.3.1"

__all__ = [
    "IndevoltAPI",
    "APIException",
    "DiscoveredDevice",
    "MINIMUM_SOC",
    "POWER_LIMITS",
    "PowerExceedsMaxError",
    "SocBelowMinimumError",
    "TimeOutException",
    "async_discover",
]
