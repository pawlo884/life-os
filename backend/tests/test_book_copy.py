import pytest


@pytest.mark.asyncio
async def test_book_copy_status(api_client):
    created = await api_client.post(
        "/api/v1/books",
        json={
            "title": "Pożyczona książka",
            "total_pages": 100,
            "copy_status": "BORROWED",
            "borrowed_from": "Marek",
        },
    )
    assert created.status_code == 201
    book = created.json()
    assert book["copy_status"] == "BORROWED"
    assert book["borrowed_from"] == "Marek"

    missing_lender = await api_client.post(
        "/api/v1/books",
        json={"title": "Bez pożyczającego", "total_pages": 50, "copy_status": "BORROWED"},
    )
    assert missing_lender.status_code == 422

    updated = await api_client.patch(
        f"/api/v1/books/{book['id']}",
        json={"copy_status": "NONE"},
    )
    assert updated.status_code == 200
    assert updated.json()["copy_status"] == "NONE"
    assert updated.json()["borrowed_from"] == "Marek"


@pytest.mark.asyncio
async def test_borrowed_stays_borrowed_when_completed_until_manual_return(api_client):
    created = await api_client.post(
        "/api/v1/books",
        json={
            "title": "Do oddania",
            "total_pages": 10,
            "copy_status": "BORROWED",
            "borrowed_from": "Ania",
            "is_active": True,
        },
    )
    book_id = created.json()["id"]

    finished = await api_client.post(
        "/api/v1/books/read",
        json={"current_page": 10, "book_id": book_id},
    )
    assert finished.status_code == 200
    result = finished.json()["book"]
    assert result["status"] == "COMPLETED"
    assert result["copy_status"] == "BORROWED"
    assert result["borrowed_from"] == "Ania"

    returned = await api_client.patch(
        f"/api/v1/books/{book_id}",
        json={"copy_status": "NONE"},
    )
    assert returned.status_code == 200
    assert returned.json()["copy_status"] == "NONE"
