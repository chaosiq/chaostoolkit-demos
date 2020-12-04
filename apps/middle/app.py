import logging

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette_exporter import PrometheusMiddleware, handle_metrics
from prometheus_client import Counter

ERROR_COUNT = Counter(
    "failed_call", "Counts of calls that failed", ("to",))


async def main(request: Request) -> JSONResponse:
    async with httpx.AsyncClient(timeout=1.0) as c:
        try:
            r = await c.get("http://back:8002")
            value = r.json().get('value')
            request.app.last_value = value
            return JSONResponse({"value": value})
        except httpx.TransportError as x:
            ERROR_COUNT.labels("back").inc()
            logging.error(
                "Failed to talk with the back service", exc_info=True)
            return JSONResponse(
                {
                    "error": x.__class__.__name__,
                    "value": request.app.last_value
                }, status_code=200)


async def health(request: Request) -> Response:
    return Response()


app = Starlette(debug=True, routes=[
    Route('/', main),
    Route('/health', health)
])
app.last_value = 0
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", handle_metrics)
