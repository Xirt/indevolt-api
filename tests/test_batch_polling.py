"""Scenarios for initialization followed by repeated batched reads."""

import json

import pytest
from aiohttp import ClientSession

from indevolt_api import (
    IndevoltAPI,
    IndevoltBattery,
    IndevoltGrid,
    IndevoltSolar,
    IndevoltSystem,
)

from .helpers import MockDevice

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("point_count", "batch_sizes"),
    [
        pytest.param(49, [49], id="below-full-batch"),
        pytest.param(50, [50], id="full-batch"),
        pytest.param(51, [50, 1], id="one-point-tail"),
        pytest.param(101, [50, 50, 1], id="multiple-full-batches-and-tail"),
    ],
)
async def test_initialize_then_repeat_batched_reads(
    api: IndevoltAPI,
    device: MockDevice,
    session: ClientSession,
    point_values: dict[str, int],
    point_count: int,
    batch_sizes: list[int],
) -> None:
    """One client initializes and reads changing snapshots in 50-point batches."""
    device.response_data = {
        "device": {
            "type": "CMS-SF2000",
            "sn": "test-serial",
            "fw": "1.2.3",
            "mac": "aa:bb:cc:11:22:33",
        }
    }

    config = await api.get_config()

    assert config["device"] == {
        "type": "CMS-SF2000",
        "generation": 2,
        "sn": "test-serial",
        "fw": "1.2.3",
        "mac": "aa:bb:cc:11:22:33",
    }
    points = [
        *IndevoltSystem,
        *IndevoltGrid,
        *IndevoltBattery,
        *IndevoltSolar,
    ][:point_count]
    batches = [points[start : start + 50] for start in range(0, len(points), 50)]

    for cycle in range(2):
        point_values.update(
            {point: cycle * 1000 + index for index, point in enumerate(points)}
        )
        snapshot: dict[str, object] = {}
        for batch in batches:
            snapshot.update(await api.fetch_data(batch))

        assert snapshot == point_values
        assert len(snapshot) == point_count

    assert device.requests[0].method == "GET"
    assert device.requests[0].path == "/rpc/Sys.GetConfig"
    reads = device.requests[1:]
    assert [request.path for request in reads] == ["/rpc/Indevolt.GetData"] * (
        len(batch_sizes) * 2
    )
    assert [request.method for request in reads] == ["POST"] * (len(batch_sizes) * 2)
    payloads = [json.loads(request.query["config"]) for request in reads]
    assert payloads == [{"t": [int(point) for point in batch]} for batch in batches] * 2
    assert [len(payload["t"]) for payload in payloads] == batch_sizes * 2
    assert [request.headers["Connection"] for request in device.requests] == [
        "close"
    ] * len(device.requests)
    assert api.session is session
    assert session.closed is False
