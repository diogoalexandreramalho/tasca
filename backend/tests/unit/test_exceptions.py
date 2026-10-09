from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.exceptions import NotFoundError, register_exception_handlers


async def test_app_exception_is_formatted_by_handler() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise NotFoundError("Reservation not found.", details={"code": "K7P2"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 404
    assert response.json() == {
        "code": "not_found",
        "message": "Reservation not found.",
        "details": {"code": "K7P2"},
    }
