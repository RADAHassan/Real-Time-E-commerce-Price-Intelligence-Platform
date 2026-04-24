"""
Unit tests for sink/app.py.
Uses FastAPI TestClient — no Bigtable emulator, no network calls.
BigtableClient is injected via _state["client"] override.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sink.app import _state, app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_state():
    """Reset shared state before every test."""
    original_client = _state["client"]
    original_metrics = dict(_state["metrics"])
    yield
    _state["client"] = original_client
    _state["metrics"].update(original_metrics)


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.write_price_item.return_value = "abc123#9999999999999999999"
    return client


@pytest.fixture
def api(mock_client):
    """TestClient with a pre-wired mock BigtableClient."""
    _state["client"] = mock_client
    return TestClient(app)


@pytest.fixture
def api_no_client():
    """TestClient with no BigtableClient (simulates startup failure)."""
    _state["client"] = None
    return TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


def test_health_returns_200(api):
    resp = api.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "uptime_seconds" in body


def test_health_bigtable_ready_true(api):
    resp = api.get("/health")
    assert resp.json()["bigtable_ready"] is True


def test_health_bigtable_ready_false(api_no_client):
    resp = api_no_client.get("/health")
    assert resp.json()["bigtable_ready"] is False


# ---------------------------------------------------------------------------
# /metrics
# ---------------------------------------------------------------------------


def test_metrics_initial_zero(api):
    _state["metrics"]["ingested"] = 0
    _state["metrics"]["errors"] = 0
    resp = api.get("/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ingested"] == 0
    assert body["errors"] == 0


# ---------------------------------------------------------------------------
# /ingest — success cases
# ---------------------------------------------------------------------------


VALID_PAYLOAD = {
    "product_id": "abc123def456abc123def456abc12345",
    "source": "jumia.ma",
    "url": "https://www.jumia.ma/hp-pavilion.html",
    "title": "HP Pavilion 15",
    "price": 4299.0,
    "currency": "MAD",
    "rating": 4.0,
    "availability": "In Stock",
    "category": "Ordinateurs Portables",
    "image_url": "https://img.jumia.ma/hp.jpg",
    "scraped_at": "2026-04-24T12:00:00+00:00",
    "pipeline": "nifi-streaming",
}


def test_ingest_success_201(api):
    resp = api.post("/ingest", json=VALID_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "ok"
    assert "row_key" in body


def test_ingest_calls_write_price_item(api, mock_client):
    api.post("/ingest", json=VALID_PAYLOAD)
    mock_client.write_price_item.assert_called_once()
    call_arg = mock_client.write_price_item.call_args[0][0]
    assert call_arg["product_id"] == VALID_PAYLOAD["product_id"]
    assert call_arg["price"] == 4299.0


def test_ingest_increments_counter(api):
    _state["metrics"]["ingested"] = 0
    api.post("/ingest", json=VALID_PAYLOAD)
    assert _state["metrics"]["ingested"] == 1


def test_ingest_optional_fields_have_defaults(api, mock_client):
    minimal = {
        "product_id": "abc",
        "source": "test.ma",
        "url": "https://test.ma/prod",
        "title": "Test Product",
        "price": 100.0,
        "currency": "MAD",
    }
    resp = api.post("/ingest", json=minimal)
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# /ingest — validation errors
# ---------------------------------------------------------------------------


def test_ingest_missing_required_field_422(api):
    bad = dict(VALID_PAYLOAD)
    del bad["product_id"]
    resp = api.post("/ingest", json=bad)
    assert resp.status_code == 422


def test_ingest_negative_price_422(api):
    bad = dict(VALID_PAYLOAD)
    bad["price"] = -10.0
    resp = api.post("/ingest", json=bad)
    assert resp.status_code == 422


def test_ingest_empty_title_422(api):
    bad = dict(VALID_PAYLOAD)
    bad["title"] = ""
    resp = api.post("/ingest", json=bad)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /ingest — service errors
# ---------------------------------------------------------------------------


def test_ingest_no_client_503(api_no_client):
    resp = api_no_client.post("/ingest", json=VALID_PAYLOAD)
    assert resp.status_code == 503
    assert "BigtableClient" in resp.json()["detail"]


def test_ingest_bigtable_exception_500(api, mock_client):
    mock_client.write_price_item.side_effect = RuntimeError("Bigtable connection refused")
    resp = api.post("/ingest", json=VALID_PAYLOAD)
    assert resp.status_code == 500
    assert _state["metrics"]["errors"] == 1


def test_ingest_bigtable_error_increments_error_counter(api, mock_client):
    _state["metrics"]["errors"] = 0
    mock_client.write_price_item.side_effect = Exception("timeout")
    api.post("/ingest", json=VALID_PAYLOAD)
    assert _state["metrics"]["errors"] == 1
