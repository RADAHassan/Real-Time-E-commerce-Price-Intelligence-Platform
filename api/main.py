"""
Price Intelligence API — read-path service.
Serves data from dbt mart tables (BigQuery) with a mock-data fallback
for local development (USE_MOCK_DATA=true).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings
from api.models import (
    HealthResponse,
    PriceAlert,
    PriceHistoryPoint,
    ProductListResponse,
    ProductPrice,
    SourceStats,
)

_state: dict = {}
_cfg = get_settings()


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(app: FastAPI):
    _state["bq_ready"] = False
    if not _cfg.use_mock_data:
        try:
            from google.cloud import bigquery  # noqa: PLC0415
            _state["bq"] = bigquery.Client(project=_cfg.gcp_project_id)
            _state["bq_ready"] = True
        except Exception as exc:
            print(f"[WARN] BigQuery unavailable — falling back to mock data: {exc}")
            _state["bq"] = None
    yield
    _state.clear()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title=_cfg.api_title,
    version=_cfg.api_version,
    description="REST API for the Real-Time E-commerce Price Intelligence Platform",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cfg.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bq_query(sql: str) -> list[dict]:
    """Run a BigQuery query and return rows as dicts."""
    bq = _state.get("bq")
    if bq is None:
        raise RuntimeError("BigQuery client not initialised")
    return [dict(row) for row in bq.query(sql).result()]


def _using_mock() -> bool:
    return _cfg.use_mock_data or not _state.get("bq_ready", False)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        bigquery_ready=_state.get("bq_ready", False),
        mock_mode=_using_mock(),
        version=_cfg.api_version,
    )


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@app.get("/api/v1/products", response_model=ProductListResponse, tags=["products"])
def list_products(
    source: Optional[str] = Query(None, description="Filter by site (e.g. jumia.ma)"),
    search: Optional[str] = Query(None, description="Full-text search on title"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> ProductListResponse:
    if _using_mock():
        from api import mock_data  # noqa: PLC0415
        rows = mock_data.get_current_prices()
    else:
        sql = f"""
            SELECT * FROM `{_cfg.gcp_project_id}.{_cfg.marts_dataset}.mart_current_prices`
            ORDER BY source, title
        """
        rows = _bq_query(sql)

    if source:
        rows = [r for r in rows if r["source"] == source]
    if search:
        term = search.lower()
        rows = [r for r in rows if term in r["title"].lower()]

    total = len(rows)
    page = rows[offset : offset + limit]
    return ProductListResponse(
        items=[ProductPrice(**r) for r in page],
        total=total,
        source_filter=source,
        search=search,
    )


@app.get("/api/v1/products/{product_id}", response_model=ProductPrice, tags=["products"])
def get_product(product_id: str) -> ProductPrice:
    if _using_mock():
        from api import mock_data  # noqa: PLC0415
        rows = [r for r in mock_data.get_current_prices() if r["product_id"] == product_id]
    else:
        sql = f"""
            SELECT * FROM `{_cfg.gcp_project_id}.{_cfg.marts_dataset}.mart_current_prices`
            WHERE product_id = '{product_id}'
            LIMIT 1
        """
        rows = _bq_query(sql)

    if not rows:
        raise HTTPException(status_code=404, detail=f"Product {product_id!r} not found")
    return ProductPrice(**rows[0])


@app.get(
    "/api/v1/products/{product_id}/history",
    response_model=list[PriceHistoryPoint],
    tags=["products"],
)
def get_product_history(
    product_id: str,
    days: int = Query(30, ge=1, le=365),
) -> list[PriceHistoryPoint]:
    if _using_mock():
        from api import mock_data  # noqa: PLC0415
        rows = mock_data.get_price_history(product_id, days)
        if not rows:
            raise HTTPException(status_code=404, detail=f"Product {product_id!r} not found")
    else:
        sql = f"""
            SELECT * FROM `{_cfg.gcp_project_id}.{_cfg.marts_dataset}.mart_price_history`
            WHERE product_id = '{product_id}'
              AND scraped_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
            ORDER BY scraped_at
        """
        rows = _bq_query(sql)

    return [PriceHistoryPoint(**r) for r in rows]


# ---------------------------------------------------------------------------
# Sources / Stats
# ---------------------------------------------------------------------------

@app.get("/api/v1/sources", response_model=list[str], tags=["stats"])
def list_sources() -> list[str]:
    return [
        "books.toscrape.com",
        "scrapeme.live",
        "jumia.ma",
        "ultrapc.ma",
        "micromagma.ma",
    ]


@app.get("/api/v1/stats", response_model=list[SourceStats], tags=["stats"])
def get_stats() -> list[SourceStats]:
    if _using_mock():
        from api import mock_data  # noqa: PLC0415
        rows = mock_data.get_stats()
    else:
        sql = f"""
            SELECT * FROM `{_cfg.gcp_project_id}.{_cfg.marts_dataset}.mart_price_stats`
            ORDER BY source
        """
        rows = _bq_query(sql)

    return [SourceStats(**r) for r in rows]


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@app.get("/api/v1/alerts", response_model=list[PriceAlert], tags=["alerts"])
def get_alerts(
    source: Optional[str] = Query(None),
    min_drop_pct: float = Query(5.0, description="Minimum drop percentage to include"),
) -> list[PriceAlert]:
    if _using_mock():
        from api import mock_data  # noqa: PLC0415
        rows = mock_data.get_alerts()
    else:
        sql = f"""
            SELECT * FROM `{_cfg.gcp_project_id}.{_cfg.marts_dataset}.mart_price_alerts`
            WHERE price_change_pct <= -{min_drop_pct}
            ORDER BY price_change_pct
        """
        rows = _bq_query(sql)

    if source:
        rows = [r for r in rows if r["source"] == source]

    return [PriceAlert(**r) for r in rows]
