import itertools

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


async def main(request: Request) -> JSONResponse:
    return JSONResponse({"value": next(request.app.count)})


app = Starlette(debug=True, routes=[
    Route('/', main),
])
app.count = itertools.count()
