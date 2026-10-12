from httpx import AsyncClient


async def test_list_slots_in_start_time_order(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/slots")

    assert response.status_code == 200
    assert [(s["service"], s["start_time"], s["end_time"]) for s in response.json()] == [
        ("lunch", "12:00:00", "13:30:00"),
        ("lunch", "13:30:00", "15:00:00"),
        ("dinner", "19:00:00", "20:30:00"),
        ("dinner", "20:30:00", "22:00:00"),
    ]


async def test_list_tables(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/tables")

    assert response.status_code == 200
    tables = response.json()
    assert len(tables) == 15
    assert tables[0] == {
        "id": 1,
        "name": "M1",
        "min_capacity": 1,
        "max_capacity": 2,
        "is_active": True,
    }
    assert tables[-1]["name"] == "M15"
    assert (tables[-1]["min_capacity"], tables[-1]["max_capacity"]) == (5, 8)
