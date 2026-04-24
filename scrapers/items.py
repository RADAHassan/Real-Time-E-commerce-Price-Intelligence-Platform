"""
PriceItem — the canonical data shape that every spider must produce.
Having a single Item class enforces a consistent schema across all sources
and is validated by ValidationPipeline before anything is written to disk or NiFi.
"""

import scrapy


class PriceItem(scrapy.Item):
    # Identity
    product_id = scrapy.Field()      # MD5 of the canonical product URL
    source = scrapy.Field()          # e.g. "books.toscrape.com"
    url = scrapy.Field()             # canonical product page URL

    # Core price data
    title = scrapy.Field()
    price = scrapy.Field()           # float — always converted from raw string
    currency = scrapy.Field()        # ISO 4217: "GBP", "USD", …

    # Enrichment
    rating = scrapy.Field()          # float 0.0–5.0 (None if unavailable)
    availability = scrapy.Field()    # normalised: "In Stock" | "Out of Stock"
    category = scrapy.Field()        # primary category string
    image_url = scrapy.Field()       # absolute URL

    # Audit
    scraped_at = scrapy.Field()      # UTC ISO-8601 timestamp
