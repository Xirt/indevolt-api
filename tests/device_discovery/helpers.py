"""Controlled network state for device discovery scenarios."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock

from indevolt_api import ActiveDiscoveryProtocol


@dataclass
class DiscoveryNetwork:
    """Controlled UDP transport, address resolution and discovery wait."""

    endpoint: AsyncMock
    transport: Mock
    protocol: ActiveDiscoveryProtocol
    wait: AsyncMock
    resolve: Mock
