import logging

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


async def main(request: Request) -> JSONResponse:
    async with httpx.AsyncClient(timeout=1.0) as c:
        try:
            r = await c.get("http://middle:8001")
            value = r.json().get('value')
            request.app.last_value = value
            return JSONResponse({"value": value})
        except httpx.TransportError as x:
            logging.error(
                "Failed to talk with the middle service", exc_info=True)
            return JSONResponse(
                {
                    "error": x.__class__.__name__,
                    "value": request.app.last_value
                }, status_code=200)


app = Starlette(debug=True, routes=[
    Route('/', main),
])
app.last_value = 0
