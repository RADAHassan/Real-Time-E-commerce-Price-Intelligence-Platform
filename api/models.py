from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ProductPrice(BaseModel):
    product_id: str
    source: str
    title: str
    url: str
    price: float
    currency: str
    rating: Optional[float] = None
    availability: str = "Unknown"
    category: Optional[str] = None
    scraped_at: datetime
    scraped_date: date


class PriceHistoryPoint(BaseModel):
    product_id: str
    price: float
    prev_price: Optional[float] = None
    price_change_pct: Optional[float] = None
    price_change_abs: Optional[float] = None
    scraped_date: date
    scraped_at: datetime


class SourceStats(BaseModel):
    source: str
    currency: str
    product_count: int
    observation_count: int
    avg_price: float
    min_price: float
    max_price: float
    median_price: float
    p25_price: float
    p75_price: float
    stddev_price: Optional[float] = None
    first_seen_date: date
    last_updated_date: date


class PriceAlert(BaseModel):
    product_id: str
    source: str
    title: str
    url: str
    currency: str
    current_price: float
    prev_price: float
    price_change_pct: float
    price_change_abs: float
    alert_date: date
    scraped_at: datetime


class ProductListResponse(BaseModel):
    items: list[ProductPrice]
    total: int
    source_filter: Optional[str] = None
    search: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    bigquery_ready: bool
    mock_mode: bool
    version: str
