"""Fixtures for device control parameter checks."""

from unittest.mock import Mock

import pytest
from aiohttp import ClientSession

from indevolt_api import IndevoltAPI


@pytest.fixture
def api_without_network() -> IndevoltAPI:
    """Provide a client for the synchronous parameter checks."""
    return IndevoltAPI("192.0.2.1", 8080, Mock(spec=ClientSession))
