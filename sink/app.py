"""
Bigtable Sink — microservice HTTP qui reçoit les PriceItems de NiFi
et les écrit dans Bigtable via BigtableClient.

Endpoints :
  POST /ingest   — écrit un PriceItem (JSON body)
  GET  /health   — health check (utilisé par Docker + NiFi)
  GET  /metrics  — compteurs simples (items ingérés, erreurs)

Variables d'environnement (depuis .env ou docker-compose) :
  GCP_PROJECT_ID        — ex: my-gcp-project
  BIGTABLE_INSTANCE_ID  — ex: price-intelligence
  BIGTABLE_EMULATOR_HOST — ex: bigtable-emulator:8086  (si émulateur)
  SINK_PORT             — port d'écoute (défaut: 8087)

Lancement local :
  uvicorn sink.app:app --host 0.0.0.0 --port 8087 --reload
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

load_dotenv()

logger = logging.getLogger("sink")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

# ---------------------------------------------------------------------------
# Shared state — injected at startup, replaced in tests via dependency override
# ---------------------------------------------------------------------------

_state: dict[str, Any] = {
    "client": None,
    "metrics": {"ingested": 0, "errors": 0, "start_time": time.time()},
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    project_id = os.getenv("GCP_PROJECT_ID", "")
    instance_id = os.getenv("BIGTABLE_INSTANCE_ID", "price-intelligence")
    if project_id:
        try:
            from bigtable.client import BigtableClient
            _state["client"] = BigtableClient(project_id, instance_id)
            logger.info("BigtableClient ready (project=%s instance=%s)", project_id, instance_id)
        except Exception as exc:
            logger.error("BigtableClient init failed: %s", exc)
    else:
        logger.warning("GCP_PROJECT_ID not set — Bigtable writes will fail")
    yield
    _state["client"] = None


app = FastAPI(
    title="Bigtable Sink",
    version="1.0.0",
    description="HTTP microservice that writes NiFi price items to Bigtable",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class PricePayload(BaseModel):
    product_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    price: float
    currency: str = Field(..., min_length=1)
    rating: float | None = None
    availability: str = "Unknown"
    category: str = ""
    image_url: str = ""
    scraped_at: str = ""
    pipeline: str = "unknown"

    @field_validator("price")
    @classmethod
    def price_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price must be >= 0")
        return v


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest(payload: PricePayload):
    """Write a single PriceItem to Bigtable."""
    client = _state["client"]
    if client is None:
        _state["metrics"]["errors"] += 1
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BigtableClient not initialised — check GCP_PROJECT_ID",
        )
    try:
        row_key = client.write_price_item(payload.model_dump())
        _state["metrics"]["ingested"] += 1
        logger.info("Ingested %s → %s", payload.source, row_key)
        return {"status": "ok", "row_key": row_key}
    except Exception as exc:
        _state["metrics"]["errors"] += 1
        logger.error("Write failed for %s: %s", payload.url, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@app.get("/health")
async def health():
    """Health check — always 200 if the process is alive."""
    uptime = int(time.time() - _state["metrics"]["start_time"])
    return {
        "status": "ok",
        "bigtable_ready": _state["client"] is not None,
        "uptime_seconds": uptime,
    }


@app.get("/metrics")
async def metrics():
    """Lightweight counters — no Prometheus dependency."""
    m = _state["metrics"]
    uptime = int(time.time() - m["start_time"])
    return {
        "ingested": m["ingested"],
        "errors": m["errors"],
        "uptime_seconds": uptime,
        "ingestion_rate": round(m["ingested"] / max(uptime, 1), 2),
    }


# ---------------------------------------------------------------------------
# Entrypoint (run directly or via Makefile)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("SINK_PORT", "8087"))
    uvicorn.run("sink.app:app", host="0.0.0.0", port=port, reload=False)
