from fastapi.testclient import TestClient

from address_ai.api.main import app


def test_health():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_endpoint():
    response = TestClient(app).post(
        "/api/search",
        json={"text": "universidad por san nicolas cerca del metro que tenga mecatronica"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["candidates"][0]["candidate"]["id"] == "mx-nl-sng-u-uanl-fime"
    assert body["parsed"]["municipality"]["value"] == "San Nicolás de los Garza"
