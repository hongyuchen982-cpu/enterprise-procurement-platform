from uuid import UUID, uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


def _header_uuid(value: str | None) -> UUID:
    if value is None:
        return uuid4()
    try:
        return UUID(value)
    except ValueError:
        return uuid4()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _header_uuid(request.headers.get("x-request-id"))
        trace_id = _header_uuid(request.headers.get("x-trace-id"))
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["x-request-id"] = str(request_id)
        response.headers["x-trace-id"] = str(trace_id)
        return response
