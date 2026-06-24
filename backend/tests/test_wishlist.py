import pytest


@pytest.mark.asyncio
async def test_wishlist_crud_and_move_to_shelf(api_client):
    create = await api_client.post(
        "/api/v1/wishlist",
        json={
            "title": "Deep Work",
            "author": "Cal Newport",
            "note": "Recommended on podcast",
            "total_pages": 296,
        },
    )
    assert create.status_code == 201
    item = create.json()
    assert item["title"] == "Deep Work"
    assert item["note"] == "Recommended on podcast"

    listed = await api_client.get("/api/v1/wishlist")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = await api_client.patch(
        f"/api/v1/wishlist/{item['id']}",
        json={"note": "Buy when finished current book"},
    )
    assert updated.status_code == 200
    assert updated.json()["note"] == "Buy when finished current book"

    moved = await api_client.post(f"/api/v1/wishlist/{item['id']}/move-to-shelf", json={})
    assert moved.status_code == 201
    book = moved.json()
    assert book["title"] == "Deep Work"
    assert book["total_pages"] == 296
    assert book["status"] == "QUEUED"

    empty = await api_client.get("/api/v1/wishlist")
    assert empty.status_code == 200
    assert empty.json() == []


@pytest.mark.asyncio
async def test_move_to_shelf_requires_pages(api_client):
    create = await api_client.post(
        "/api/v1/wishlist",
        json={"title": "Unknown pages book"},
    )
    item_id = create.json()["id"]

    failed = await api_client.post(f"/api/v1/wishlist/{item_id}/move-to-shelf", json={})
    assert failed.status_code == 400

    ok = await api_client.post(
        f"/api/v1/wishlist/{item_id}/move-to-shelf",
        json={"total_pages": 200},
    )
    assert ok.status_code == 201
    assert ok.json()["total_pages"] == 200
