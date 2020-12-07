from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette_exporter import PrometheusMiddleware, handle_metrics


async def main(request: Request) -> JSONResponse:
    return JSONResponse({"message": "hello world"})


async def health(request: Request) -> Response:
    return Response()


async def force_failure():
    raise RuntimeError("kaboom")


app = Starlette(debug=True, routes=[
    Route('/', main),
    Route('/health', health)
])
app.last_value = 0
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", handle_metrics)
# this will make our probe unstartable
app.add_event_handler("startup", force_failure)