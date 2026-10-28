import asyncio
import uuid

import pytest


@pytest.mark.asyncio
async def test_create_and_update_preserves_created_at(client, auth_headers):
    order_id = str(uuid.uuid4())
    created = await client.post(
        "/api/orders", json={"order_id": order_id, "status": "pending"}, headers=auth_headers
    )
    assert created.status_code == 200
    updated = await client.post(
        "/api/orders", json={"order_id": order_id, "status": "completed"}, headers=auth_headers
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "completed"
    assert updated.json()["created_at"] == created.json()["created_at"]


@pytest.mark.asyncio
async def test_validation_and_authentication(client, auth_headers):
    assert (await client.get("/api/orders")).status_code == 401
    invalid = await client.post(
        "/api/orders", json={"order_id": "not-a-uuid", "status": ""}, headers=auth_headers
    )
    assert invalid.status_code == 422
    missing = await client.post("/api/orders", json={}, headers=auth_headers)
    assert missing.status_code == 422


@pytest.mark.asyncio
async def test_filters_pagination_and_date_validation(client, auth_headers):
    ids = [str(uuid.uuid4()) for _ in range(3)]
    created_date = None
    for index, order_id in enumerate(ids):
        response = await client.post(
            "/api/orders",
            json={"order_id": order_id, "status": "completed" if index < 2 else "pending"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        created_date = response.json()["created_at"][:10]

    response = await client.get(
        "/api/orders?status=completed&page=1&limit=1", headers=auth_headers
    )
    body = response.json()
    assert response.status_code == 200
    assert len(body["data"]) == 1
    assert body["pagination"] == {"page": 1, "limit": 1, "total": 2, "total_pages": 2}

    by_id = await client.get(f"/api/orders?order_id={ids[2]}", headers=auth_headers)
    assert by_id.json()["data"][0]["status"] == "pending"
    by_date = await client.get(
        f"/api/orders?start_date={created_date}&end_date={created_date}", headers=auth_headers
    )
    assert by_date.json()["pagination"]["total"] == 3
    outside_date = await client.get(
        "/api/orders?start_date=1999-01-01&end_date=1999-01-01", headers=auth_headers
    )
    assert outside_date.json()["pagination"]["total"] == 0
    invalid_dates = await client.get(
        "/api/orders?start_date=2026-10-29&end_date=2026-10-28", headers=auth_headers
    )
    assert invalid_dates.status_code == 422


@pytest.mark.asyncio
async def test_concurrent_upserts_do_not_duplicate(client, auth_headers):
    order_id = str(uuid.uuid4())
    responses = await asyncio.gather(
        *[
            client.post(
                "/api/orders",
                json={"order_id": order_id, "status": f"state-{index}"},
                headers=auth_headers,
            )
            for index in range(10)
        ]
    )
    assert all(response.status_code == 200 for response in responses)
    result = await client.get(f"/api/orders?order_id={order_id}", headers=auth_headers)
    assert result.json()["pagination"]["total"] == 1
