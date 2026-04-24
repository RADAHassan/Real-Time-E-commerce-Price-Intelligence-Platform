"""
Realistic mock data for local development without GCP credentials.
Mirrors the shape of the dbt mart tables.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import random

_BASE_DATE = date(2024, 4, 1)
_NOW = datetime(2024, 4, 24, 10, 0, 0)

_PRODUCTS_RAW = [
    # books.toscrape.com (GBP)
    {"product_id": "a1b2c3d4", "source": "books.toscrape.com", "currency": "GBP",
     "title": "A Light in the Attic", "price": 51.77, "rating": 3.0, "category": "Poetry"},
    {"product_id": "e5f6g7h8", "source": "books.toscrape.com", "currency": "GBP",
     "title": "Tipping the Velvet", "price": 53.74, "rating": 1.0, "category": "Historical Fiction"},
    {"product_id": "i9j0k1l2", "source": "books.toscrape.com", "currency": "GBP",
     "title": "Soumission", "price": 50.10, "rating": 1.0, "category": "Fiction"},
    {"product_id": "m3n4o5p6", "source": "books.toscrape.com", "currency": "GBP",
     "title": "Sharp Objects", "price": 47.82, "rating": 4.0, "category": "Mystery"},
    # scrapeme.live (GBP)
    {"product_id": "q7r8s9t0", "source": "scrapeme.live", "currency": "GBP",
     "title": "Bulbasaur #001", "price": 63.00, "rating": 4.5, "category": "Pokemon"},
    {"product_id": "u1v2w3x4", "source": "scrapeme.live", "currency": "GBP",
     "title": "Charmander #004", "price": 88.00, "rating": 5.0, "category": "Pokemon"},
    {"product_id": "y5z6a7b8", "source": "scrapeme.live", "currency": "GBP",
     "title": "Squirtle #007", "price": 55.00, "rating": 4.0, "category": "Pokemon"},
    # jumia.ma (MAD)
    {"product_id": "c9d0e1f2", "source": "jumia.ma", "currency": "MAD",
     "title": "HP Laptop 15s Core i5 12th Gen", "price": 5999.0, "rating": 4.2, "category": "Laptops"},
    {"product_id": "g3h4i5j6", "source": "jumia.ma", "currency": "MAD",
     "title": "Samsung Galaxy A54 5G 128GB", "price": 2799.0, "rating": 4.5, "category": "Smartphones"},
    {"product_id": "k7l8m9n0", "source": "jumia.ma", "currency": "MAD",
     "title": 'Lenovo IdeaPad 3 15" Intel Core i3', "price": 4299.0, "rating": 3.8, "category": "Laptops"},
    {"product_id": "o1p2q3r4", "source": "jumia.ma", "currency": "MAD",
     "title": "iPhone 14 128GB", "price": 9999.0, "rating": 4.8, "category": "Smartphones"},
    # ultrapc.ma (MAD)
    {"product_id": "s5t6u7v8", "source": "ultrapc.ma", "currency": "MAD",
     "title": "ASUS ROG Strix G15 Ryzen 7", "price": 12500.0, "rating": None, "category": "Gaming Laptops"},
    {"product_id": "w9x0y1z2", "source": "ultrapc.ma", "currency": "MAD",
     "title": "MSI GF63 Core i5 RTX 3050", "price": 8900.0, "rating": None, "category": "Gaming Laptops"},
    {"product_id": "a3b4c5d6", "source": "ultrapc.ma", "currency": "MAD",
     "title": "Dell Inspiron 15 3520 Core i7", "price": 7200.0, "rating": None, "category": "Laptops"},
    # micromagma.ma (MAD)
    {"product_id": "e7f8g9h0", "source": "micromagma.ma", "currency": "MAD",
     "title": "Acer Aspire 5 Core i5 12th Gen 8GB SSD 512GB", "price": 6299.0, "rating": None, "category": "Laptops"},
    {"product_id": "i1j2k3l4", "source": "micromagma.ma", "currency": "MAD",
     "title": "HP 255 G9 AMD Ryzen 5 8GB", "price": 4799.0, "rating": None, "category": "Laptops"},
]


def _make_product(raw: dict, days_ago: int = 0) -> dict:
    scraped_at = _NOW - timedelta(days=days_ago, hours=random.randint(0, 3))
    return {
        **raw,
        "url": f"https://www.{raw['source']}/{raw['product_id']}.html",
        "availability": random.choice(["In Stock", "In Stock", "In Stock", "Out of Stock"]),
        "image_url": None,
        "scraped_at": scraped_at.isoformat() + "Z",
        "scraped_date": (scraped_at.date()).isoformat(),
    }


def get_current_prices() -> list[dict]:
    return [_make_product(p) for p in _PRODUCTS_RAW]


def get_price_history(product_id: str, days: int = 30) -> list[dict]:
    raw = next((p for p in _PRODUCTS_RAW if p["product_id"] == product_id), None)
    if not raw:
        return []

    history = []
    base_price = raw["price"]
    prev_price = None
    for d in range(days, -1, -1):
        # simulate small random daily price fluctuation
        noise = random.uniform(-0.03, 0.02)
        price = round(base_price * (1 + noise), 2)
        scraped_at = _NOW - timedelta(days=d)
        pct = round((price - prev_price) / prev_price * 100, 2) if prev_price else None
        history.append({
            "product_id": product_id,
            "price": price,
            "prev_price": prev_price,
            "price_change_pct": pct,
            "price_change_abs": round(price - prev_price, 2) if prev_price else None,
            "scraped_date": scraped_at.date().isoformat(),
            "scraped_at": scraped_at.isoformat() + "Z",
        })
        prev_price = price
    return history


def get_stats() -> list[dict]:
    from collections import defaultdict
    import statistics

    groups: dict[tuple, list[float]] = defaultdict(list)
    for p in _PRODUCTS_RAW:
        groups[(p["source"], p["currency"])].append(p["price"])

    result = []
    for (source, currency), prices in groups.items():
        s = sorted(prices)
        n = len(s)
        result.append({
            "source": source,
            "currency": currency,
            "product_count": n,
            "observation_count": n * 7,
            "avg_price": round(sum(prices) / n, 2),
            "min_price": round(min(prices), 2),
            "max_price": round(max(prices), 2),
            "median_price": round(statistics.median(prices), 2),
            "p25_price": round(s[n // 4], 2),
            "p75_price": round(s[3 * n // 4], 2),
            "stddev_price": round(statistics.stdev(prices), 2) if n > 1 else 0.0,
            "first_seen_date": (_BASE_DATE - timedelta(days=30)).isoformat(),
            "last_updated_date": _BASE_DATE.isoformat(),
        })
    return result


def get_alerts() -> list[dict]:
    alerts = []
    for p in _PRODUCTS_RAW:
        # Simulate a ~15% drop for some products
        if hash(p["product_id"]) % 4 == 0:
            prev = round(p["price"] * 1.18, 2)
            pct = round((p["price"] - prev) / prev * 100, 2)
            alerts.append({
                "product_id": p["product_id"],
                "source": p["source"],
                "title": p["title"],
                "url": f"https://www.{p['source']}/{p['product_id']}.html",
                "currency": p["currency"],
                "current_price": p["price"],
                "prev_price": prev,
                "price_change_pct": pct,
                "price_change_abs": round(p["price"] - prev, 2),
                "alert_date": _BASE_DATE.isoformat(),
                "scraped_at": _NOW.isoformat() + "Z",
            })
    return sorted(alerts, key=lambda x: x["price_change_pct"])
