"""Scenarios for resuming device polling after a failed batch."""

import json

import pytest
from aiohttp import ClientError, ClientSession

from indevolt_api import IndevoltAPI, IndevoltBattery

from ..helpers import MockDevice

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("status", "body", "expected_error"),
    [
        pytest.param(503, None, ClientError, id="http-error"),
        pytest.param(200, "not-json", json.JSONDecodeError, id="invalid-json"),
    ],
)
async def test_failed_batch_can_be_followed_by_a_new_read_cycle(
    api: IndevoltAPI,
    device: MockDevice,
    session: ClientSession,
    point_values: dict[str, int],
    status: int,
    body: str | None,
    expected_error: type[Exception],
) -> None:
    """Polling can restart after a failed batch on the same client and session."""
    points = list(IndevoltBattery)[:51]
    first_batch = points[:50]
    last_batch = points[50:]
    point_values.update({point: index for index, point in enumerate(points)})

    assert await api.fetch_data(first_batch) == {
        point: point_values[point] for point in first_batch
    }

    device.status = status
    device.body = body
    with pytest.raises(expected_error):
        await api.fetch_data(last_batch)

    assert len(device.requests) == 2
    assert session.closed is False

    device.status = 200
    device.body = None
    point_values.update({point: 1000 + index for index, point in enumerate(points)})
    snapshot: dict[str, object] = {}
    for batch in (first_batch, last_batch):
        snapshot.update(await api.fetch_data(batch))

    assert snapshot == point_values
    assert [json.loads(request.query["config"]) for request in device.requests] == [
        {"t": [int(point) for point in first_batch]},
        {"t": [int(point) for point in last_batch]},
        {"t": [int(point) for point in first_batch]},
        {"t": [int(point) for point in last_batch]},
    ]
    assert session.closed is False
