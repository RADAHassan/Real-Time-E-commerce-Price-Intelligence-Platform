"""
API endpoint tests — always run in mock mode (USE_MOCK_DATA=true).
No GCP credentials required.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("USE_MOCK_DATA", "true")
os.environ.setdefault("GCP_PROJECT_ID", "test-project")

from api.main import app  # noqa: E402  (must be after env setup)


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health_returns_200(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_mock_mode_true(client: TestClient) -> None:
    data = resp = client.get("/health").json()
    assert data["mock_mode"] is True
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def test_list_products_returns_items(client: TestClient) -> None:
    resp = client.get("/api/v1/products")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] > 0
    assert len(body["items"]) > 0


def test_list_products_item_shape(client: TestClient) -> None:
    item = client.get("/api/v1/products").json()["items"][0]
    for field in ("product_id", "source", "title", "price", "currency", "scraped_at"):
        assert field in item, f"Missing field: {field}"


def test_list_products_filter_by_source(client: TestClient) -> None:
    resp = client.get("/api/v1/products?source=jumia.ma")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["source"] == "jumia.ma"


def test_list_products_search(client: TestClient) -> None:
    resp = client.get("/api/v1/products?search=hp")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert "hp" in item["title"].lower()


def test_list_products_pagination(client: TestClient) -> None:
    page1 = client.get("/api/v1/products?limit=2&offset=0").json()["items"]
    page2 = client.get("/api/v1/products?limit=2&offset=2").json()["items"]
    assert page1 != page2


def test_get_product_by_id(client: TestClient) -> None:
    products = client.get("/api/v1/products").json()["items"]
    pid = products[0]["product_id"]
    resp = client.get(f"/api/v1/products/{pid}")
    assert resp.status_code == 200
    assert resp.json()["product_id"] == pid


def test_get_product_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/products/nonexistent-id")
    assert resp.status_code == 404


def test_get_product_history(client: TestClient) -> None:
    products = client.get("/api/v1/products").json()["items"]
    pid = products[0]["product_id"]
    resp = client.get(f"/api/v1/products/{pid}/history?days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 8  # days+1 points
    assert all("price" in p for p in data)


def test_get_history_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/products/bad-id/history")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Sources & Stats
# ---------------------------------------------------------------------------

def test_list_sources(client: TestClient) -> None:
    resp = client.get("/api/v1/sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert "jumia.ma" in sources
    assert "books.toscrape.com" in sources
    assert len(sources) == 5


def test_get_stats(client: TestClient) -> None:
    resp = client.get("/api/v1/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert len(stats) > 0
    row = stats[0]
    for field in ("source", "currency", "avg_price", "product_count", "median_price"):
        assert field in row


def test_stats_avg_price_positive(client: TestClient) -> None:
    for row in client.get("/api/v1/stats").json():
        assert row["avg_price"] > 0
        assert row["min_price"] <= row["avg_price"] <= row["max_price"]


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

def test_get_alerts(client: TestClient) -> None:
    resp = client.get("/api/v1/alerts")
    assert resp.status_code == 200
    alerts = resp.json()
    assert isinstance(alerts, list)


def test_alerts_all_have_negative_pct(client: TestClient) -> None:
    for alert in client.get("/api/v1/alerts").json():
        assert alert["price_change_pct"] < 0


def test_alerts_filter_by_source(client: TestClient) -> None:
    resp = client.get("/api/v1/alerts?source=jumia.ma")
    assert resp.status_code == 200
    for alert in resp.json():
        assert alert["source"] == "jumia.ma"
