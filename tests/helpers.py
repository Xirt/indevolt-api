"""Local HTTP device simulator shared by the client tests."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from aiohttp import web


@dataclass
class RecordedRequest:
    """An HTTP request received by the simulated device."""

    method: str
    path: str
    query: dict[str, str]
    headers: dict[str, str]
    body: bytes


@dataclass
class MockDevice:
    """Configurable responses and captured requests for a local device."""

    host: str = "127.0.0.1"
    port: int = 0
    response_data: object = field(default_factory=dict)
    status: int = 200
    body: str | None = None
    content_type: str = "application/json"
    requests: list[RecordedRequest] = field(default_factory=list)
    responder: Callable[[RecordedRequest], web.Response] | None = None

    async def handle(self, request: web.Request) -> web.Response:
        """Capture the wire request and return the configured response."""
        recorded = RecordedRequest(
            method=request.method,
            path=request.path,
            query=dict(request.query),
            headers=dict(request.headers),
            body=await request.read(),
        )
        self.requests.append(recorded)
        if self.body is not None:
            return web.Response(
                text=self.body, status=self.status, content_type=self.content_type
            )
        if self.responder is not None:
            return self.responder(recorded)
        return web.json_response(self.response_data, status=self.status)


DeviceFactory = Callable[[], Awaitable[MockDevice]]
